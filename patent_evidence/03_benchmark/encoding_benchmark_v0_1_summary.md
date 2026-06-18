# GeoTask Encoding Benchmark v0.1 — Summary

> **Deterministic simulated benchmark.** Does not claim live LLM accuracy.

## Token Cost by Encoding

| Encoding | Avg Input Tokens | Avg Output Tokens | Avg Total Tokens |
|----------|-----------------:|------------------:|-----------------:|
| natural_language | 174 | 229 | 403 |
| geotask_yaml | 197 | 64 | 261 |
| compact_dsl | 79 | 11 | 90 |

## Normalization & Verification Success

| Encoding | Normalization Success Rate | Verification Success Rate | Avg Benchmark Score |
|----------|---------------------------:|--------------------------:|--------------------:|
| natural_language | 1.00 | 1.00 | 79.6 |
| geotask_yaml | 1.00 | 1.00 | 81.9 |
| compact_dsl | 1.00 | 1.00 | 95.0 |

## Token Reduction vs Natural Language

| Metric | Value |
|--------|-------|
| Compact DSL avg total tokens | 90 |
| Natural Language avg total tokens | 403 |
| Token reduction | 77.6% |
| Compression ratio | 4.5× |

## Core Conclusion

Compact DSL reduced average total token estimate from **403** to **90** compared with natural language input, approximately a **77.6%** reduction or **4.5×** compression, while preserving **100%** normalization success and correct verification status detection in the **deterministic simulated benchmark**.

> 在确定性模拟 benchmark 中，Compact DSL 相比自然语言输入，将平均 total token 估算值从 **403** 降至 **90**，约减少 **77.6%**，约为 **4.5×** 压缩；同时保持 **100%** 归一化成功率，并能够正确识别 verified、contradicted 和 need_review 等验证状态。

## Notes

- Model outputs are deterministic simulated outputs for benchmark reproducibility. This benchmark evaluates encoding cost, normalization behavior, verification behavior, contradiction detection, and review-reason generation. It does not claim live LLM accuracy.
- Token counts are approximate and used only for relative comparison between encoding formats.
