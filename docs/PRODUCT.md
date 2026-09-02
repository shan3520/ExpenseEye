# Product

## Register

product

## Users

Financially savvy users optimizing spending. They analyze personal finances in private settings to understand spending patterns and optimize their cash flow.

## Product Purpose

ExpenseEye reads a bank statement the way an analyst would. It closes a finance-ops loop: detect the recurring charges, project when each should land, match that expected ledger against what the statement actually contains, and report a match rate together with the exceptions it could not resolve — both the expected charges that never arrived and the charges no schedule accounts for.

Six read-outs: cash-flow forecast, transaction categorization, anomaly detection, subscription radar, recurring reconciliation, and overspending analysis.

## Privacy Model

Statements are parsed **server-side**, not in the browser. Each upload gets its own SQLite database in a temp directory, keyed by a session id; it is deleted when the session ends and reaped automatically after a TTL (default 30 minutes). No account, no persistence beyond the session, no third-party sharing.

This is deliberately stated as "session-scoped and deleted", not "never leaves your device" — the data does reach the server, and claiming otherwise would be untrue of the hosted demo. Users who want the stronger guarantee can self-host, which the MIT licence and a single Flask service make straightforward.

## Brand Privacy

Privacy-focused, trustworthy, analytical

## Anti-references

Slow, enterprise-feeling financial software - avoiding bloated, slow banking software that feels corporate and unresponsive.

## Design Principles

- Privacy as a core feature: session-scoped processing, deleted on exit, no account, self-hostable — described in the terms above rather than overclaimed
- Trustworthy insights: every number is traceable. Accuracy is back-tested and reported, including when it is bad; skipped rows carry a reason; the reconciliation loop publishes what it could NOT match, because a match rate without an exception list proves nothing
- Analytical precision: Clear, actionable financial analytics that empower decision-making
- Performance focused: Fast, responsive interface that respects user's time
- Accessibility first: Inclusive design that works for all users

## Accessibility & Inclusion

WCAG 2.1 AA compliance, color blindness friendly palettes, reduced motion preferences respected