# AI工具实测001：Microsoft MarkItDown

把Word/PDF整理成Markdown，再交给AI处理：先验证转换结果。

官方项目：https://github.com/microsoft/markitdown

MarkItDown是微软开源的Python文档转换工具/CLI，基础转换不是聊天模型，也不是浏览器扩展。本例用0.1.9版，只测试本地DOCX与PDF，不接LLM、不启用OCR插件或Azure云转换。

## 本期实际结果

三个输入是同一份合成日报的不同格式，没有真实客户资料。

| 输入 | 本次实际结果 |
| --- | --- |
| Word | 3,041.20元保留；三列表格的7行数据（含合计）计数对应完整 |
| 有文字层PDF | 金额保留，但部分计数如5、3、1、30被拆到表格行外，需要检查结构 |
| 纯图片扫描PDF | CLI退出码0，输出却是0字节；基础本地路径没有OCR |

真实转换结果未人工修订。`demo/content-audit.json`保存错位原文；`demo/cli-log.json`是实际命令与退出状态。可用文件生成，不等于表格和内容已经正确。

## 文件

`demo/inputs/`：Word、文本PDF、同页图片PDF。
`demo/converted/`：基础Python接口的实际Markdown输出，空文件也是实际结果。
`demo/cli-output/`：实际CLI输出，与Python接口结果逐字节一致。
`demo/run_demo.py`：读取本目录输入并转换；运行中阻止出站socket连接，验证本例本地路径。
`demo/validation.json`：版本、输入输出校验和、字数和运行记录。
`demo/content-audit.json`：逐项检查及PDF结构问题。

## 自己跑一次

先安装Python。官方当前支持3.10–3.14；本次实测macOS arm64、Python3.12.14。以下在解压后的本目录运行：

```bash
python3 -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell可使用 .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python demo/run_demo.py
```

也可以在同一虚拟环境里逐个用CLI转换：

```bash
python -m markitdown demo/inputs/report.docx -o word-result.md
python -m markitdown demo/inputs/report-text.pdf -o pdf-result.md
python -m markitdown demo/inputs/report-scan.pdf -o scan-result.md
```

首次安装依赖需要网络。运行基础转换不需要模型API key。本包已有示例输出，重复运行会覆盖示例的`demo/converted/`和`demo/validation.json`，想保留原记录请复制目录后执行。

`environment-lock.txt`记录本次实际安装版本，用于排查差异，不代表已在其他系统逐一验证。修改输入或启用额外OCR/云转换，结果和费用条件可能变化；脚本中的断言只验收这三个固定示例。

## 交给AI助手的任务

```text
先阅读本目录README。创建隔离Python环境，安装requirements.txt，
运行demo/run_demo.py，检查实际输出，不要只看退出码。
逐项核对Word表格中的类别和计数，指出PDF里计数被拆到行外的例子，
检查扫描PDF的输出是否为空。保留原始转换结果和日志，不手工改成成功。
```

## 我会怎么用

有Word源文件优先测试源文件；表格逐项核对。纯图片扫描件先补文字识别，再检查提取结果。转换成Markdown不代表模型已经理解或认证了文档结论。要做高保真版式转换或完整OCR，需另选路径和测试。

官方依据：
- https://github.com/microsoft/markitdown/blob/main/README.md
- https://github.com/microsoft/markitdown/releases/tag/v0.1.9

观察与实测日期：2026-11-01。此包是固定合成案例，附工具使用记录，不包含第三方模型、依赖源码或模型权重。
