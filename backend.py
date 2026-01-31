from flask import Flask, jsonify
import pandas as pd
import networkx as nx

app = Flask(__name__)

# -------------------------------
# CORE ANALYSIS FUNCTION
# -------------------------------
def run_analysis():

    # Load data
    df = pd.read_csv("data/transactions.csv")

    # Clean & standardize
    df = df.drop(columns=['Unnamed: 0'], errors='ignore')
    df = df.rename(columns={
        'sender': 'From',
        'receiver': 'To',
        'amount': 'Value',
        'timestamp': 'TimeStamp'
    })

    df = df[df['Value'] > 0]
    df['TimeStamp'] = pd.to_datetime(df['TimeStamp'], unit='s')

    # Build graph
    G = nx.DiGraph()
    for _, row in df.iterrows():
        G.add_edge(
            row['From'],
            row['To'],
            value=row['Value'],
            timestamp=row['TimeStamp']
        )

    # -------------------------------
    # PATTERN DETECTION
    # -------------------------------
    fan_out_wallets = []
    fan_in_wallets = []
    peeling_wallets = []

    for node in G.nodes():
        out_edges = list(G.out_edges(node, data=True))
        in_edges = list(G.in_edges(node, data=True))

        # Fan-out
        if len(out_edges) >= 5:
            times = [e[2]['timestamp'] for e in out_edges]
            if (max(times) - min(times)).total_seconds() <= 3600:
                fan_out_wallets.append(node)

        # Fan-in
        if len(in_edges) >= 5:
            times = [e[2]['timestamp'] for e in in_edges]
            if (max(times) - min(times)).total_seconds() <= 3600:
                fan_in_wallets.append(node)

        # Peeling
        if len(in_edges) == 1 and len(out_edges) == 1:
            in_val = in_edges[0][2]['value']
            out_val = out_edges[0][2]['value']
            if out_val < in_val and out_val > 0.9 * in_val:
                peeling_wallets.append(node)

    # -------------------------------
    # SCORING
    # -------------------------------
    suspicion_score = {}

    for node in G.nodes():
        score = 0
        if node in fan_out_wallets:
            score += 3
        if node in fan_in_wallets:
            score += 3
        if node in peeling_wallets:
            score += 2
        suspicion_score[node] = score

    # -------------------------------
    # CONNECTION-DISTANCE SCORING
    # -------------------------------
    known_illicit_wallets = fan_out_wallets[:3]
    distance_score = {}
    MAX_HOPS = 3

    for seed in known_illicit_wallets:
        lengths = nx.single_source_shortest_path_length(G, seed, cutoff=MAX_HOPS)
        for node, dist in lengths.items():
            s = MAX_HOPS - dist + 1
            distance_score[node] = max(distance_score.get(node, 0), s)

    for node in suspicion_score:
        suspicion_score[node] += distance_score.get(node, 0)

    # Normalize scores (0–10)
    max_score = max(suspicion_score.values()) if suspicion_score else 1
    for node in suspicion_score:
        suspicion_score[node] = round((suspicion_score[node] / max_score) * 10, 2)

    # -------------------------------
    # EXPORT RESULTS
    # -------------------------------
    results = []
    for node, score in suspicion_score.items():
        results.append({
            "wallet": node,
            "score": score,
            "fan_out": node in fan_out_wallets,
            "fan_in": node in fan_in_wallets,
            "peeling_chain": node in peeling_wallets
        })


    return results


# -------------------------------
# API ENDPOINTS
# -------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "Backend running"})


@app.route("/analyze")
def analyze():
    return jsonify({"message": "Analysis completed"})


@app.route("/results")
def results():
    data = run_analysis()
    return jsonify(data)


# -------------------------------
# RUN SERVER
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
