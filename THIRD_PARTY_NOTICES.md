# Data attribution and redistribution notice

Dataset: **Bank Marketing**, UCI Machine Learning Repository, dataset 222.
Source: https://archive.ics.uci.edu/dataset/222/bank+marketing
License: **Creative Commons Attribution 4.0 International (CC BY 4.0)**,
https://creativecommons.org/licenses/by/4.0/ — verified on 2026-10-12.
Legal text: https://creativecommons.org/licenses/by/4.0/legalcode

Current UCI dataset citation:

Moro, S., Rita, P., & Cortez, P. (2014). *Bank Marketing* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5K306.

The unmodified legacy `bank-names.txt` identifies Paulo Cortez and Sérgio Moro as creators and requests the following earlier paper citation for this version:

Moro, S., Laureano, R., & Cortez, P. (2011). *Using Data Mining for Bank Direct Marketing: An Application of the CRISP-DM Methodology*. In P. Novais et al. (Eds.), Proceedings of the European Simulation and Modelling Conference, ESM'2011, pp. 117–121, Guimarães, Portugal. EUROSIS. https://hdl.handle.net/1822/14838

The legacy paper is cited as requested; its PDF is not redistributed here. The current UCI citation does not imply that the 20-input bank-additional variant was used in this project.

Preserved files: official outer `bank-marketing.zip`, nested `bank.zip`, extracted `bank-full.csv` and `bank-names.txt`. Exact SHA-256 values and byte lengths are recorded in config/dataset_lock.json and data/source/provenance.json. Archives and extracted files are unchanged. The outer archive contains other versions as supplied by UCI; those versions are not consumed by the project pipeline.

Project changes: we add zero-based row references, deterministic train/validation/test assignments, an 11-column input policy, and training-only audit summaries. No raw values, labels, original ordering, or original file bytes have been changed. Nothing suggests endorsement by the creators, UCI, the bank, or the cited authors.

CC BY permits redistribution and adaptation with attribution, a license link and indication of changes. Preserve this notice and the original notices when sharing data or derived material. No additional restriction is imposed on recipients' rights to the licensed data. Repository privacy is a collaboration setting, not a replacement license.

The dataset license is not asserted over course materials, group manuals, software dependencies, or unrelated content. Restricted course and planning PDFs are excluded from this repository. Dependencies retain their own licenses; no dependency source is vendored.
