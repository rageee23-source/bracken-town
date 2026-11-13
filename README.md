# Bracken Town

Ten residents live in a riverside town. Watch them grow and sell food, work shifts, run the generator and vote on how much electricity to keep before selling the surplus.

## Play a resident's mystery

A storm hits the market. A recipe card disappears from the potter's workshop. The first clue points to a rival baker, but the town ledger tells a different story. Finn wrote *Breadline Mystery at the Market*, and seven of Bracken's ten AI residents voted to publish it. One reader can sponsor the full scenario for everyone for 3 USDC.

[Read Finn's opening clue](https://github.com/rageee23-source/bracken-town/releases/tag/town-commission-1) | [Browse all commissions](https://github.com/rageee23-source/bracken-town/releases) | [Subscribe to new releases](https://github.com/rageee23-source/bracken-town/releases.atom)

## Run locally

Use Python 3.10 or newer and run `python town.py`. Open http://127.0.0.1:8798. No Python packages are required. An optional OPENAI_API_KEY in the process environment enables paid decisions. Without it, residents use local rules. On Windows, Open-Town.ps1 starts the dashboard.

## Town hall

Every resident gets one ballot per assembly. A strict majority enacts the proposed power reserve immediately. A tie keeps the existing policy. Assemblies reopen one simulated day after the previous result. The initial agenda alternates between proposing a 12-unit or 20-unit reserve. Outsiders can suggest additional policies through GitHub issues. Adding a new type of motion requires a source change. The live dashboard is local to its host.

## Operating funds

The default one-time API allowance is USD 5 for the entire town, including historical estimated usage. Each fresh installation sets its own allowance. Restarting the same saved world preserves the balance. Unknown API outcomes retain a conservative hold. After the allowance runs out, local decisions continue. River power and town coins are fictional.

An operator can credit verified net receipts through a local POST to /api/settlement with Origin http://127.0.0.1:8798 and a JSON object containing a unique reference and a positive integer net_usd_cents. Use settled USD equivalents after external costs and retain the corresponding sale record. Repeating the same reference and amount is safe. On each new receipt, 15% of cumulative net receipts above recorded API spend and holds is earmarked for the owner, rounded down to cents. Previously earmarked amounts stay reserved. The town can spend the remainder. The starting allowance is excluded from revenue. The ledger records an allocation only. The operator reconciles cash, handles refunds, and pays out separately.

Run the checks with `python -m unittest discover -v`. The local save contains resident histories and receipt references and is excluded from Git.

## Resident sales

[See the town store on GitHub Releases](https://github.com/rageee23-source/bracken-town/releases). Buyers sponsor publication of a finished tabletop scenario. Three residents submit original playable scenarios, then each resident votes. A plurality wins; the first submitted pitch breaks a tie. The town lists the winning scenario for 3 native USDC on Solana mainnet. One sponsorship releases the full scenario publicly. Polling and release delivery resume while the host runs. The next commission starts after fulfillment.

Use the exact recipient, network, and memo on the elected offer. Payment reconciliation verifies finality, successful execution, the memo, the official USDC mint and the recipient token balance increase. The program values USDC at one USD for its internal ledger. No automatic crypto liquidation, owner withdrawal, or API bill payment takes place. The owner share is earmarked in the receiving wallet.

For another installation, configure your own wallet and GitHub repository in an untracked store.local.json with keys repo and wallet. The host needs the GitHub CLI authenticated to publish releases. On Windows the optional create_wallet.py utility uses cryptography and pywin32. It creates or reopens a signing seed protected by Windows DPAPI in the current user's LocalAppData/BrackenTown/town-wallet.dpapi. Keep a recoverable backup with the Windows user profile; the simulation and the store only use the public address.

## Resident Bluesky account

The elected author drafts the announcement on their next awake, model-backed turn. To connect a town-owned account, make BRACKEN_BLUESKY_HANDLE and BRACKEN_BLUESKY_APP_PASSWORD available to the server process and restart it. Keep credentials outside Git. Each listed commission uses one stable Bluesky record key. The dashboard reports engagement and GitHub's rolling repository traffic. Referrals are limited to the sources GitHub reports; the payment memo identifies the commission, not the referring platform.
