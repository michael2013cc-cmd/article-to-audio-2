# md2audio：把书面文档变成能听的 MP3

一套把 Markdown / 长文改写成**听稿**、再合成成带章节导航的 MP3 的流水线。

它解决的不是"文字转语音"，而是三个具体的麻烦：

1. **书面结构没法听。** 表格、脚注、缩写、多层小标题，眼睛能扫，耳朵跟不上。所以流水线的第一环不是 TTS，是一份*手写的听稿*。
2. **一小时的文件不可导航。** 输出的 MP3 带 ID3v2.4 `CHAP`/`CTOC` 章节表，播放器里直接是分节列表，不用拖进度条。
3. **手机上声音太小。** 原始 TTS 大约 −18 LUFS，而且峰值还会溢出，结果是"又小声又糊"。这里的目标是 −13 LUFS 左右、真峰值安全低于 0 dBFS。

外部依赖只有一个网络服务：微软 Edge 的免费神经语音（经 `edge-tts`）。**没有 API key，没有配额，也没有任何 SLA**——所以每一章节的合成都是 5 次重试加退避。其余全部本地完成（ffmpeg + mutagen）。

---

## 快速开始

```bash
sudo apt install ffmpeg            # 或 brew install ffmpeg
pip install -r requirements.txt

# 1) 检查听稿：章节对不对，数字和杂字符有没有问题
python -m md2audio parse examples/sample.txt
python -m md2audio audit examples/sample.txt --source examples/source_example.md

# 2) 合成（约 3 分钟音频，几十秒跑完；80 分钟音频大约 5–6 分钟）
python -m md2audio make examples/sample.txt \
    -o out/sample.mp3 \
    --title "久坐办公：每小时站起来三分钟" \
    --album "md2audio 示例" --artist "md2audio" --year 2026

# 3) 单独复检任何一个 MP3
python -m md2audio check out/sample.mp3 --chapters 4
```

`make` 会同时产出 `out/sample.txt`——一份**带时间点的文字稿**，索引和正文都对齐到音频秒数。听长内容时它是可 grep 的目录。

中途断网了？已合成的章节留在 `out/sample_work/`，加 `--resume` 重跑即可跳过。

---

## 听稿格式

纯文本，一节一个标记行，正文照读：

```
@@P0|开场：这份东西是什么，以及三句必须先听到的安全话
第一段，直接会被读出来。

第二段。

@@P1|理论基石：为什么大脑能改写输入通道
……
```

* `@@` 开头才算章节标记；`ID` 只是标签，播放器里显示的是标题。
* 第一个标记之前不能有正文（会被 `ValueError` 拒绝，而不是静默合成出一整坨）。
* 空行分段。正文一字不改地送进 TTS——**你想怎么被读到，就怎么写**，而不是怎么排版。

---

## 从 Markdown 到听稿：改写规则

这一步是人工的（或人工盯着的），也是质量的来源。规则是从几次实际返工里总结的：

**表格 → 固定顺序的散文。** 每张表按这个顺序念一遍：*这是什么 → 证据数字 → 机制 → 对你是打折还是成立 → 怎么自测 → 什么时候停*。列的顺序换来换去都听得懂，是因为顺序固定，而不是因为表清楚。

**缩写第一次出现就展开。** `VWFA`、`logMAR`、`tDCS` 这类缩写在耳朵里没有意义。第一次出现写全，后面可以用短名，但一节课里最好不要超过三四个短名。

**数字用中文写。** `百分之二十五`、`二零一五年`、`每三十分钟`。`25%` 在不少语音引擎里会被逐字符读，节奏全毁。

**每节结尾三句小结。** 八节就是八次"刚才说到哪儿了"的重置，长内容才听得完。

**开场给地图，结尾给背诵清单。** 开场一节说明"接下来有几段、分别讲什么"；最后一节把该记的东西按重要性列一遍。

**分清"报告说的"和"我加的"。** 推论、外推、口径换算要显式标记（"这是我的推断，不是原文的说法"）。听音频时人无法回头核对来源，这一句标注的成本很低、价值很高。

**诚实限定要写在结论旁边，不是脚注里。** 样本量、观察期、结局指标的类型——"短期生理指标会变好"不等于"你会少生病"。

---

## 数字纪律（这个仓库里最容易出事的地方）

一次真实事故：听稿把某个年份写成"二零二三"，而源文档是 2015。朗读时没人听得出来，只有回看文字稿才发现。

`audit` 子命令不做判断，只把清单摊开给人核对：

| 输出字段 | 用途 |
|----------|------|
| `spelled_years` | 所有中文拼写的年份，逐个对回源文档 |
| `unmatched_numbers` | 听稿里有、源文档里没有的数字（凭空出现的年份/倍数就在这里） |
| `source_only_numbers` | 源文档里有、听稿里没找到的数字。**注意**：听稿把数字写成中文时这一栏会很长，属正常，它是一张"这些内容我有没有漏掉"的清单 |
| `latin_runs` | 白名单之外的拉丁/西里尔字符段，用来抓没翻完的占位文字 |
| `non_cjk_characters` | 出现在中文稿里不该有的其它语种字符（真实事故：一段西里尔残留） |

章节标记行会被剔除后再扫描——`@@P0` 不会被朗读，不该被报警。

合成前跑一次 `audit`，几秒钟，省掉一次 80 分钟的返工。

---

## 响度：这些常数是怎么来的

`audio.py` 里的链路：

```
acompressor=threshold=-22dB:ratio=6:attack=5:release=200:makeup=12,
equalizer=f=2800:t=q:w=1.4:g=3,
volume=10dB,
alimiter=limit=0.76:attack=3:release=150:level=disabled
→ -ar 44100 -ac 2 -b:a 64k
```

* **限幅器上限是 0.76，不是 0.80。** 后面还要 MP3 编码，编码本身会有过冲；0.80 实测把成品推到 **+0.28 dBFS**，也就是削波。
* **2800 Hz 抬 3 dB。** 手机外放的音色偏闷，人声清晰度主要在这一带。
* **刻意用立体声。** 单声道在手机喇叭上听着薄。
* **64 kbps。** 对纯语音足够透明，一小时文件约 28 MB，方便传到手机上。

`verify.py` 的验收线（`tests/test_verify_parse.py` 记录了一次解析事故）：

| 指标 | 目标 |
|------|------|
| 综合响度 | −16 ~ −11 LUFS |
| 真峰值 | ≤ −0.1 dBFS |
| flat factor | 0.0（持续数字静音＝削波） |
| 解码 | 无错误 |
| 章节数 | 等于听稿节数 |

改任何一条滤镜参数之后，都要重新跑 `check`。示例文件当前实测：−12.8 LUFS / 真峰值 −1.4 dBFS / flat factor 0.0 / 4 章。

拼接用 `-c copy`（无损），并且必须 `-write_xing 1`，否则播放器显示的长度是错的。

**章节锚点必须从归一化之后的分节文件量出来**，不能用原始合成件：限幅器和编码器会改变每节几十毫秒，八节累积起来跳转点就明显偏了。

---

## 章节标签的坑

`tags.py`：

* mutagen 的文本帧参数是 `text=`，不是 `desc=`。用 `desc=` 会写出**空帧**，读回来直接 `KeyError: 'TIT2'`。
* 保存写 `v2_version=4`，没有 `v2_4=` 这个参数。
* 无害但会困惑人的一点：存 v2.4 时 `TYER` 会被升级成 `TDRC`。
* 顺序问题：先 `shutil.copyfile` 把成品音频放到目标路径，**再**打标签。对着不存在的路径保存标签，会生成一个只有标签的几百字节文件，看起来像成功。
* **`CTOC` 没有 `is_top=` 和 `child=` 这两个参数。** 子项在 `child_element_ids`，顶层标志在 `flags` 字节的 `0x02`（`CTOCFlags.TOP_LEVEL`）。传错参数名不会报错，mutagen 会当成无关 kwarg 丢掉 —— 结果是目录帧写出来子项是空的、`flags=0`，**章节导航表里什么都没有**。只有直接扫 CHAP 帧的播放器还看得到章节。
* 因此 `verify.py` 除了数 CHAP 帧，还要核对目录帧的子项确实覆盖了每一个 CHAP。`tags.read_toc()` 读回来，`check` 会报 `table of contents does not list every chapter`。

---

## Windows

**Windows 是支持的，但有两个坑，本仓库已经处理掉。**

**编码。** Windows 的控制台默认用传统代码页（繁中机器上是 cp950），而 Python 在输出被重定向时用的是 ANSI 代码页而不是控制台的 UTF-8。于是两处会崩：

* `print()` 一个代码页装不下的章节标题 → `UnicodeEncodeError`，直接中断；
* `subprocess.run(..., text=True)` 解码 ffmpeg 的输出 → `UnicodeDecodeError`，`stderr` 变成 `None`，`verify._summary(None)` 再抛一个 `AttributeError`。

修法在 `md2audio/__init__.py`（导入时就把 stdout/stderr 改成 UTF-8）和 `audio.py` / `verify.py`（`subprocess.run(..., encoding="utf-8", errors="replace")`）。**你不需要设 `PYTHONUTF8=1`**。

**运行方式。** 本仓库不是安装包，用 `PYTHONPATH` 指向仓库根目录即可：

```powershell
$env:PYTHONPATH = "C:\path\to\article-to-audio-2"
python -m md2audio make examples\sample.txt -o out\sample.mp3
```

或者 `pip install -e .` 之后直接用 `md2audio` 命令。

---

## 代码结构

| 模块 | 责任 |
|------|------|
| `script.py` | 听稿格式：解析 / 序列化，格式错误立刻抛 |
| `synth.py` | edge-tts 合成，每节一个请求，5 次重试 |
| `audio.py` | 响度链路、分节归一化、无损拼接、时长 |
| `tags.py` | ID3v2.4 `CHAP`/`CTOC` 章节表与基本标签 |
| `verify.py` | 实测响度 / 峰值 / flat factor / 解码 / 章节数，给出通过与否 |
| `transcript.py` | 带时间点的文字稿 |
| `audit.py` | 数字与杂字符的机械审计 |
| `pipeline.py` | 串起五个阶段，可 `--resume` |

测试不联网、不需要 ffmpeg：`python -m unittest discover -s tests`（28 项）。

---

## 使用边界

* **上游是免费的公共端点。** 它没有公开文档、可能变动、也可能限流。别把它当生产服务；批量任务请换本地 TTS（`audio.py`/`tags.py`/`verify.py` 与合成引擎无关，只需要一个能产出 mp3 的 `synth_text`）。
* **听稿可能非常私人。** 这个仓库只放流水线代码和一份虚构示例。你写的稿子（疾病、康复、身体测量、个人计划）默认应该被 `.gitignore` 挡住，别提交。
* **音频里的内容不会自动变准确。** 数字审计只是把待查清单摊开；结论的正确性仍要人负责。
* 合成的长音频请自己确认收听场景适合——这套东西是为"通勤/躺着听一份长报告"设计的。

## 许可

MIT，见 `LICENSE`。
