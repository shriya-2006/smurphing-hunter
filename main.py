import pandas as pd

df = pd.read_csv("data/transactions.csv")
# standardize column names

df = df.drop(columns=['Unnamed: 0'], errors='ignore')

df = df.rename(columns={
    'sender': 'From',
    'receiver': 'To',
    'amount': 'Value',
    'timestamp': 'TimeStamp'
})


# remove zero value tx
df = df[df['Value'] > 0]

# convert timestamp
df['TimeStamp'] = pd.to_datetime(df['TimeStamp'], unit='s')

print(df.head())
import networkx as nx

G = nx.DiGraph()

for _, row in df.iterrows():
    G.add_edge(
        row['From'],
        row['To'],
        value=row['Value'],
        timestamp=row['TimeStamp']
    )

print("Nodes:", G.number_of_nodes())
print("Edges:", G.number_of_edges())
fan_out_wallets = []

for node in G.nodes():
    out_edges = list(G.out_edges(node, data=True))

    if len(out_edges) >= 5:
        times = [e[2]['timestamp'] for e in out_edges]
        time_diff = max(times) - min(times)

        if time_diff.total_seconds() <= 3600:
            fan_out_wallets.append(node)

print("Fan-out wallets:", len(fan_out_wallets))

fan_in_wallets = []

for node in G.nodes():
    in_edges = list(G.in_edges(node, data=True))

    if len(in_edges) >= 5:
        times = [e[2]['timestamp'] for e in in_edges]
        time_diff = max(times) - min(times)

        if time_diff.total_seconds() <= 3600:
            fan_in_wallets.append(node)

print("Fan-in wallets:", len(fan_in_wallets))

peeling_wallets = []

for node in G.nodes():
    in_edges = list(G.in_edges(node, data=True))
    out_edges = list(G.out_edges(node, data=True))

    if len(in_edges) == 1 and len(out_edges) == 1:
        in_val = in_edges[0][2]['value']
        out_val = out_edges[0][2]['value']

        if out_val < in_val and out_val > 0.9 * in_val:
            peeling_wallets.append(node)

print("Peeling wallets:", len(peeling_wallets))

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

print("Sample scores:", list(suspicion_score.items())[:5])

# ===== CONNECTION-DISTANCE FROM ILLICIT WALLETS =====

# Treat high-confidence fan-out wallets as illicit seeds
known_illicit_wallets = fan_out_wallets[:3]   # take up to 3 seeds safely

distance_score = {}
MAX_HOPS = 3

for seed in known_illicit_wallets:
    lengths = nx.single_source_shortest_path_length(G, seed, cutoff=MAX_HOPS)

    for node, dist in lengths.items():
        # closer wallets get higher score
        score = (MAX_HOPS - dist + 1)
        distance_score[node] = max(distance_score.get(node, 0), score)

# merge distance score into suspicion score
for node in suspicion_score:
    suspicion_score[node] += distance_score.get(node, 0)

print("Distance-based scoring added")

# ---- NORMALIZE SCORES TO 0–10 ----
max_score = max(suspicion_score.values())

for node in suspicion_score:
    suspicion_score[node] = round((suspicion_score[node] / max_score) * 10, 2)

# ---- TOP 10 RISKY WALLETS ----
top10 = sorted(
    suspicion_score.items(),
    key=lambda x: x[1],
    reverse=True
)[:10]

print("\nTop 10 most suspicious wallets:")
for wallet, score in top10:
    print(wallet, "→ score:", score)

# build suspicious subgraph
suspects = [n for n, s in suspicion_score.items() if s >= 3]

sub_nodes = set()
for n in suspects:
    sub_nodes.add(n)
    sub_nodes.update(G.successors(n))
    sub_nodes.update(G.predecessors(n))

H = G.subgraph(sub_nodes)

print("Subgraph nodes:", H.number_of_nodes())
print("Subgraph edges:", H.number_of_edges())

import matplotlib.pyplot as plt

pos = nx.random_layout(H)   # no SciPy needed

node_colors = []
node_sizes = []

for node in H.nodes():
    score = suspicion_score.get(node, 0)

    if score >= 6:
        node_colors.append('red')        # high-risk
        node_sizes.append(250)

    elif score >= 3:
        node_colors.append('orange')     # medium-risk
        node_sizes.append(140)

    elif score == 0:
        node_colors.append('green')      # safe wallet
        node_sizes.append(40)

    else:
        node_colors.append('lightgray')  # context
        node_sizes.append(20)


plt.figure(figsize=(10, 10))

nx.draw(
    H,
    pos,
    node_color=node_colors,
    node_size=node_sizes,
    edge_color='gray',
    alpha=0.35,
    arrows=True,
    arrowsize=10
)

plt.title("Suspicious Laundering Subgraph")
plt.show()

# -------- FAN-OUT EXAMPLE VISUAL --------
if fan_out_wallets:
    seed = fan_out_wallets[0]

    fanout_nodes = set([seed])
    fanout_nodes.update(G.successors(seed))

    H_fanout = G.subgraph(fanout_nodes)
    pos_fanout = nx.shell_layout(H_fanout)

    colors = ['red' if n == seed else 'orange' for n in H_fanout.nodes()]

    plt.figure(figsize=(6, 6))
    nx.draw(
        H_fanout,
        pos_fanout,
        node_color=colors,
        node_size=200,
        edge_color='gray'
    )
    plt.title("Fan-Out (Smurfing) Pattern")
    plt.show()

    # -------- FAN-IN EXAMPLE VISUAL --------
if fan_in_wallets:
    seed = fan_in_wallets[0]

    fanin_nodes = set([seed])
    fanin_nodes.update(G.predecessors(seed))

    H_fanin = G.subgraph(fanin_nodes)
    pos_fanin = nx.shell_layout(H_fanin)

    colors = ['red' if n == seed else 'orange' for n in H_fanin.nodes()]

    plt.figure(figsize=(6, 6))
    nx.draw(
        H_fanin,
        pos_fanin,
        node_color=colors,
        node_size=200,
        edge_color='gray'
    )
    plt.title("Fan-In (Aggregation) Pattern")
    plt.show()

results = []

for node, score in suspicion_score.items():
    if score >= 3:
        results.append({
            "wallet": node,
            "suspicion_score": score,
            "fan_out": node in fan_out_wallets,
            "fan_in": node in fan_in_wallets,
            "peeling_chain": node in peeling_wallets
        })

pd.DataFrame(results).to_csv("suspicious_wallets.csv", index=False)
print("Exported suspicious_wallets.csv")


