# Bracken Town

Ten residents live in a riverside town. Watch them grow and sell food, work shifts, run the generator and vote on how much electricity to keep before selling the surplus.

## Run locally

Use Python 3.10 or newer and run `python town.py`. Open http://127.0.0.1:8798. No Python packages are required. An optional OPENAI_API_KEY in the process environment enables paid decisions. Without it, residents use local rules. On Windows, Open-Town.ps1 starts the dashboard.

## Town hall

Every resident gets one ballot per assembly. A strict majority enacts the proposed power reserve immediately. A tie keeps the existing policy. Assemblies reopen one simulated day after the previous result. The initial agenda alternates between proposing a 12-unit or 20-unit reserve. Outsiders can suggest additional policies through GitHub issues. Adding a new type of motion requires a source change. The live dashboard is local to its host.

## Operating funds

The default one-time API allowance is USD 5 for the entire town, including historical estimated usage. Each fresh installation sets its own allowance. Restarting the same saved world preserves the balance. Unknown API outcomes retain a conservative hold. After the allowance runs out, local decisions continue. River power and town coins are fictional.

An operator can credit verified net receipts through a local POST to /api/settlement with Origin http://127.0.0.1:8798 and a JSON object containing a unique reference and a positive integer net_usd_cents. Use settled USD equivalents after external costs and retain the corresponding sale record. Repeating the same reference and amount is safe. On each new receipt, 15% of cumulative net receipts above recorded API spend and holds is earmarked for the owner, rounded down to cents. Previously earmarked amounts stay reserved. The town can spend the remainder. The starting allowance is excluded from revenue. The ledger records an allocation only. The operator reconciles cash, handles refunds, and pays out separately.

Run the checks with `python -m unittest discover -v`. The local save contains resident histories and receipt references and is excluded from Git.
