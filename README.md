## Money Laundering Detection in Blockchain Graphs

### Overview
This project detects money laundering patterns in blockchain transactions
using graph-based analysis.

### Methodology
1. Transactions are modeled as a directed graph (wallets = nodes, transfers = edges)
2. Smurfing is detected using fan-out patterns
3. Aggregation is detected using fan-in patterns
4. Peeling chains identify intermediary wallets
5. Temporal bursts are used to model transaction activity
6. Risk is propagated using hop-distance from illicit wallets
7. Each wallet is assigned a normalized suspicion score (0–10)

### Outputs
- Suspicious subgraph visualizations
- Fan-out and fan-in pattern examples
- Ranked list of high-risk wallets
- Exported CSV with wallet-level risk evidence
