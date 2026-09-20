# ming-qa

端到端 QA 验收工具包：`skills/` 下 8 个 skill + 一个 Python CLI。
运行时**零第三方依赖**（只用标准库），开发期只多一个 pytest。

## 常用命令

```bash
cd skills/quality-assurance-agent
python -m pytest tests/ -q          # 48 个测试文件；任何改动后必跑

cd ../..                             # 回仓库根
python skills/quality-assurance-agent/scripts/qa_agent.py check-mojibake . --strict
```

## 改动的验收标准

**修 bug 必须验证判别力**：把修复回滚掉，确认对应用例**变红**，再恢复。

只写一个「能通过」的测试不算完成——要能证明它在**没有这个修复时会失败**。
仓库里既有提交都按这条做过，新改动请保持一致。

## 这个仓库特有的三个坑

1. **提交信息不要用 heredoc 传中文。** Windows + Git Bash 会把中文写成乱码字符
   （U+FFFD），而 pytest 抓不到——它扫仓库文件，不扫 git 历史。
   稳妥做法：用 Write 写进临时文件，再 `git commit -F <文件>`。
   注意：本文件自身也不能出现那个字面字符，否则会被 `test_source_mojibake` 判违规。

2. **提交前确认 git 身份。** 全局配置是公司邮箱；本仓库已用**仓库级**身份覆盖为
   `mingdui`。不要动全局配置，也不要把它改回去。

3. **内部标识扫描会拒绝合并。** CI 拦内部项目名、业务词、私有网段 IP
   （规则见 `.github/workflows/ci.yml` 的 `SENTINELS`）。
   写测试示例用中性词，IP 用 RFC 5737 文档网段（`192.0.2.x`）。
   业务模块名和 API 路径也在此列——它们最容易从内部项目抄进测试注释。

## `qa_agent.py` 是 11000 行单文件

改动前按函数名定位，别整文件读。主要入口：

| 区域 | 函数 |
|---|---|
| CLI 分发 | `build_parser` · `run_with_env` · `aggregate_runs` · `render_report` |
| 门禁 | `assert_completion_data` · `check_evidence_integrity` · `assert_oracle_mapping_data` · `assert_readiness_data` |
| 覆盖投影 | `project_risk_coverage` · `_case_risk_ids` |
| 报告自检 | `qa_self_check` · `_check_sc0*` |
| 生成 spec-task | `build_spec_task` · `oracle_for_spec_task` |
| 配置解析 | `load_config` · `parse_simple_yaml` / `parse_scalar` · `load_services_config` |
| 执行与证据 | `run_cmd` · `gate_env` · `_record_run_sidecar` · `_parse_run_sidecar` |

`qa_core/` 目前只有一个模块，其余逻辑全在 `qa_agent.py`。**这是已知的结构债。**

## 文档分工（别互相抄，会漂）

- `CONTRIBUTING.md` —— 给人：环境、仓库结构、提交规范、新增 skill 的步骤
- `docs/` —— 给使用者：安装、配置、架构
- 本文件 —— 给在仓库里干活的 agent：命令、隐性规范、踩坑点
