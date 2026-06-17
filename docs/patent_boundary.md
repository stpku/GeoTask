# GeoTask Patent Boundary

## What Patents Cover

GeoTask-related patents protect the **system and method**, not individual
data files or format strings:

| Element                 | Patent Coverage                                       |
|-------------------------|-------------------------------------------------------|
| YAML file format        | **NOT** patentable (data format)                      |
| Spatial task representation | Method for encoding spatial problems for LLM processing |
| Object-operator-proposition binding | Linking objects, operations, and tasks in a verifiable structure |
| Agent orchestration     | Coordinating LLM agents for spatial reasoning            |
| Deterministic verification | Running local operators to verify LLM outputs          |
| Output normalization    | Extracting structured results from unstructured LLM text |

**Important**: Patent documents should use neutral terminology such as
"spatial task intermediate representation" rather than brand names.
GeoTask is a brand name, not a patent term.

---

## What Open Sourcing Core Does NOT Do

1. **Does not waive patent rights.** Publishing Core under MIT does not
   grant a patent license. Patent rights are retained separately.

2. **Does not open the commercial modules.** The UAV Rule Pack, Audit
   Backend, and Production Runtime remain proprietary.

3. **Does not limit future patent filings.** Core is a foundation.
   Future innovations in spatial AI verification may be patented.

---

## Guidelines for Contributors

- Do **not** disclose unreleased commercial features or algorithms.
- Do **not** include proprietary rule packs, data connectors, or customer
  configurations in pull requests.
- Do **not** publish mechanisms that are still under patent review.

If you are unsure whether something is safe to include, ask before
submitting.

---

## For Patent-Related Inquiries

Contact the GeoTask maintainers through official channels. Do not discuss
patent strategy in public issues or pull requests.
