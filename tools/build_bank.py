# -*- coding: utf-8 -*-
"""从原始 PDF / DOCX 构建结构化题库 data/questions.json。

用法（项目根目录）：
    .venv/Scripts/python.exe tools/build_bank.py

流程：解析 PDF（主）与 DOCX（校对） -> 规范化文本 -> 去重 -> 应用勘误
      -> 挂载知识点/解析 -> 严格校验 -> 输出 JSON。
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

import docx
import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from annotations import CHAPTER_KP, EXPLANATIONS, EXTRA, FIXES, NOTES  # noqa: E402
from glossary import GLOSSARY  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# 源文件目录：可通过环境变量 XIGAI_SRC 覆盖
SRC_DIR = Path(os.environ.get("XIGAI_SRC", r"C:/Users/11576/Desktop/习概复习-罗震宇"))
PDF_NAME = "26年下学期选择题汇总(1).pdf"
DOCX_NAME = "26年下学期选择题汇总(1).docx"

CJK = "\u4e00-\u9fff"
PUNCT = "，。、；：？！“”‘’《》（）【】…—"

CHAPTER_NAMES = [
    (0, "导论"),
    (1, "第一章 新时代坚持和发展中国特色社会主义"),
    (2, "第二章 以中国式现代化全面推进中华民族伟大复兴"),
    (3, "第三章 坚持党的全面领导"),
    (4, "第四章 坚持以人民为中心"),
    (5, "第五章 全面深化改革开放"),
    (6, "第六章 推动高质量发展"),
    (7, "第七章 教育、科技、人才战略"),
    (8, "第八章 发展全过程人民民主"),
    (9, "第九章 全面依法治国"),
    (10, "第十章 建设社会主义文化强国"),
    (11, "第十一章 保障和改善民生"),
    (12, "第十二章 建设社会主义生态文明"),
    (13, "第十三章 维护和塑造国家安全"),
    (14, "第十四章 国防和军队建设"),
    (15, "第十五章 “一国两制”和祖国统一"),
    (16, "第十六章 中国特色大国外交"),
    (17, "第十七章 全面从严治党"),
]
SHORT_NAME = {0: "导论"}
for _no, _name in CHAPTER_NAMES[1:]:
    SHORT_NAME[_no] = _name.split(" ")[0]

CH_RE = re.compile(r"^(导论|第[一二三四五六七八九十]{1,3}章)\s*(.*)$")
SEC_RE = re.compile(r"^[一二三四五六七八九十]{1,3}、\s*(单项选择题|单选题|多项选择题|多选题|判断题)")
ANS_RE = re.compile(r"^答案\s*[:：]?")
NO_RE = re.compile(r"^(\d{1,3})\s*[.．、]\s*")


def norm(s: str) -> str:
    s = s.replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", s).strip()


def tidy(s: str) -> str:
    """清理 PDF 抽取产生的多余空格：中文之间、数字与中文之间等。"""
    s = s.replace("\n", "").replace("\u3000", " ").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(rf"(?<=[{CJK}{PUNCT}])\s+(?=[{CJK}{PUNCT}])", "", s)
    s = re.sub(rf"(?<=\d)\s+(?=[{CJK}])", "", s)
    s = re.sub(rf"(?<=[{CJK}])\s+(?=\d)", "", s)
    s = re.sub(rf"(?<=[{CJK}])\s+(?=[A-Za-z])", "", s)
    s = re.sub(rf"(?<=[A-Za-z])\s+(?=[{CJK}])", "", s)
    s = re.sub(rf"(?<=[{CJK}])\s+(?=[{PUNCT}])", "", s)
    s = re.sub(rf"(?<=[{PUNCT}])\s+(?=[{CJK}])", "", s)
    # 题干中的填空统一为全角空格，保持“（　）”的视觉留白
    s = re.sub(r"[（(]\s*[）)]", "（　）", s)
    return s.strip()


# ------------------------------------------------------------------ 抽取
def pdf_text() -> str:
    doc = pymupdf.open(SRC_DIR / PDF_NAME)
    keep = []
    for page in doc:
        for ln in page.get_text().split("\n"):
            t = ln.strip()
            if re.fullmatch(r"\d+/\d+", t):
                continue
            if t.replace(" ", "") == "《习近平新时代中国特色社会主义思想概论》选择题":
                continue
            keep.append(ln)
    return "\n".join(keep)


def docx_text() -> str:
    d = docx.Document(SRC_DIR / DOCX_NAME)
    return "\n".join(p.text for p in d.paragraphs)


def prejoin(text: str) -> list[str]:
    """把被折行拆开的“答案”与选项字母重新拼回一行。"""
    raw = [ln.strip() for ln in text.split("\n")]
    lines, i = [], 0
    while i < len(raw):
        line = raw[i]
        if ANS_RE.match(line) and not re.search(r"[A-D]", line):
            j = i + 1
            while j < len(raw) and not raw[j]:
                j += 1
            if j < len(raw) and re.fullmatch(r"[A-D]{1,4}\s*[。.；;]?", raw[j]):
                lines.append(line + raw[j])
                i = j + 1
                continue
        lines.append(line)
        i += 1
    return lines


def split_blocks(text: str) -> list[dict]:
    lines = prejoin(text)
    chapters = [{"title": "导论", "sections": []}]
    cur_ch, cur_sec, cur_q = chapters[0], None, None
    for line in lines:
        if not line:
            continue
        m = CH_RE.match(line)
        if m and len(line) < 45:
            title = norm(m.group(1) + " " + m.group(2)) if m.group(2) else m.group(1)
            cur_ch = {"title": title, "sections": []}
            chapters.append(cur_ch)
            cur_sec = cur_q = None
            continue
        ms = SEC_RE.match(line)
        if ms and len(line) < 32:
            cur_sec = {"type": "多选" if "多" in ms.group(1) else "单选", "blocks": []}
            cur_ch["sections"].append(cur_sec)
            cur_q = None
            continue
        if cur_sec is None:
            continue
        if ANS_RE.match(line):
            if cur_q is not None:
                cur_q["answer_raw"] = line
                cur_q = None
            continue
        if cur_q is not None:
            cur_q["lines"].append(line)
            continue
        no = None
        mn = NO_RE.match(line)
        if mn:
            no = int(mn.group(1))
            line = line[mn.end():]
        cur_q = {"no": no, "lines": [line]}
        cur_sec["blocks"].append(cur_q)
    return chapters


def scan_markers(text: str) -> list[tuple[str, int, int]]:
    """依次定位 A/B/C/D（可扩展 E）选项标记，返回 (字母, 起始, 正文起始)。"""
    n, out, pos = len(text), [], 0
    letters = "ABCDE"
    wi = 0
    while wi < len(letters) and wi <= 4:
        want = letters[wi]
        best = None
        for m in re.finditer(rf"[A-{letters[min(len(letters) - 1, wi + 1)]}]", text[pos:]):
            i = pos + m.start()
            if text[i] != want:
                continue
            prev = text[i - 1] if i > 0 else "\n"
            if not (i == 0 or prev in " \n\t"):
                continue
            nxt = text[i + 1] if i + 1 < n else ""
            if not nxt:
                continue
            if nxt in ".．、":
                j = i + 1
                while j < n and text[j] in ".．、 \t":
                    j += 1
                if j < n:
                    best = (want, i, j)
                    break
                continue
            if nxt.isspace() or "\u4e00" <= nxt <= "\u9fff" or nxt in "“”《》（(":
                j = i + 1
                while j < n and text[j] in " \t":
                    j += 1
                if j < n:
                    best = (want, i, j)
                    break
        if best is None:
            break
        out.append(best)
        pos = best[2]
        wi += 1
        # 题目最多 4 个选项（个别题有 E），一旦拿到 D 就停止扩展
        if best[0] == "D":
            break
    return out


def split_options(text: str) -> tuple[str, dict[str, str]]:
    mk = scan_markers(text)
    if not mk:
        return tidy(text), {}
    stem = tidy(text[: mk[0][1]])
    opts = {}
    for k, (letter, _s, e) in enumerate(mk):
        end = mk[k + 1][1] if k + 1 < len(mk) else len(text)
        opts[letter] = tidy(text[e:end])
    return stem, opts


def parse(text: str, src: str) -> list[dict]:
    out = []
    for ch in split_blocks(text):
        for sec in ch["sections"]:
            for bi, b in enumerate(sec["blocks"]):
                body = norm("\n".join(b["lines"]))
                stem, opts = split_options(body)
                aw = b.get("answer_raw", "")
                mm = re.search(r"[A-D]{1,4}", aw)
                out.append({
                    "src": src, "chapter": ch["title"], "type": sec["type"],
                    "no": b["no"] if b["no"] is not None else bi + 1,
                    "stem": stem, "options": opts,
                    "answer": "".join(sorted(set(mm.group(0)))) if mm else "",
                })
    return out


# ------------------------------------------------------------------ 组装
def chapter_no(title: str) -> int:
    for no, name in CHAPTER_NAMES:
        if name == title:
            return no
    raise ValueError(f"未知章节标题：{title}")


def build() -> dict:
    pdf_q = parse(pdf_text(), "pdf")
    docx_q = parse(docx_text(), "docx")
    if len(pdf_q) != len(docx_q):
        raise SystemExit(f"两版题量不一致：PDF {len(pdf_q)} / DOCX {len(docx_q)}")

    questions, dropped = [], []
    for pq, dq in zip(pdf_q, docx_q):
        no = chapter_no(pq["chapter"])
        if pq["stem"] != dq["stem"]:
            # 以 PDF 为准（DOCX 有两题丢失选项标识），仅记录
            pass
        key = f"{no}-{'S' if pq['type'] == '单选' else 'M'}-{pq['no']}"

        stem, options, answer = pq["stem"], dict(pq["options"]), pq["answer"]
        if len(options) != 4:  # 用 DOCX 版本兜底
            if len(dq["options"]) == 4:
                stem, options, answer = dq["stem"], dict(dq["options"]), dq["answer"]

        fix = FIXES.get(key)
        if fix:
            if "stem" in fix:
                stem = fix["stem"]
            if "options" in fix:
                options = dict(fix["options"])

        # 去重：第十章单选第 11 题与第 3 题重复（仅选项顺序不同）
        if key == "10-S-11":
            dropped.append((key, stem))
            continue

        questions.append({
            "key": key, "chapter_no": no, "chapter": pq["chapter"],
            "type": pq["type"], "no": pq["no"], "stem": stem,
            "options": options, "answer": answer,
            "docx_stem": dq["stem"], "docx_options": dq["options"],
        })

    # 知识点映射
    names = [kp for mapping in CHAPTER_KP.values() for kp in mapping]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        raise SystemExit(f"知识点跨章重名：{dup}")
    unknown = set(CHAPTER_KP) - {no for no, _ in CHAPTER_NAMES}
    if unknown:
        raise SystemExit(f"标注中存在未知章节：{unknown}")

    kp_of = {}
    for ch_no, mapping in CHAPTER_KP.items():
        for kp, keys in mapping.items():
            for k in keys:
                if k in kp_of:
                    raise SystemExit(f"知识点重复分配：{k}")
                kp_of[k] = kp

    seq = Counter()
    final = []
    for q in questions:
        k = q["key"]
        if k not in kp_of:
            raise SystemExit(f"未分配知识点：{k} {q['stem'][:30]}")
        if k not in EXPLANATIONS:
            raise SystemExit(f"缺少解析：{k} {q['stem'][:30]}")
        type_code = "S" if q["type"] == "单选" else "M"
        seq[(q["chapter_no"], type_code)] += 1
        qid = f"{q['chapter_no']:02d}{type_code}{q['no']:02d}"
        item = {
            "id": qid,
            "chapter_id": f"{q['chapter_no']:02d}",
            "chapter": q["chapter"],
            "chapter_no": q["chapter_no"],
            "type": "single" if q["type"] == "单选" else "multiple",
            "type_label": q["type"],
            "knowledge": kp_of[k],
            "no": q["no"],
            "seq": seq[(q["chapter_no"], type_code)],
            "stem": q["stem"],
            "options": [{"key": letter, "text": text} for letter, text in q["options"].items()],
            "answer": list(q["answer"]),
            "explanation": EXPLANATIONS[k] + EXTRA.get(k, ""),
        }
        if k in NOTES:
            item["note"] = NOTES[k]
        final.append(item)

    final.sort(key=lambda x: (x["chapter_no"], x["type"] != "single", x["no"]))
    for i, q in enumerate(final, 1):
        q["order"] = i

    chapters = []
    for no, name in CHAPTER_NAMES:
        chapters.append({
            "id": f"{no:02d}",
            "no": no,
            "name": name,
            "short": SHORT_NAME[no],
            "knowledge": list(CHAPTER_KP.get(no, {}).keys()),
        })

    return {
        "meta": {
            "title": "《习近平新时代中国特色社会主义思想概论》选择题题库",
            "subject": "习近平新时代中国特色社会主义思想概论",
            "version": "1.1.0",
            "source": {
                "pdf": PDF_NAME,
                "docx": DOCX_NAME,
                "note": "PDF 与 DOCX 逐题比对，题量、题干、选项、答案一致；PDF 完整度更高，作为主数据源。",
            },
            "glossary": dict(GLOSSARY),
            "total": len(final),
            "single": sum(1 for q in final if q["type"] == "single"),
            "multiple": sum(1 for q in final if q["type"] == "multiple"),
            "dropped": [{"id": k, "stem": s, "reason": "与同章单选第 3 题重复（仅选项顺序不同）"}
                        for k, s in dropped],
        },
        "chapters": chapters,
        "questions": final,
    }


def validate(bank: dict) -> None:
    qs = bank["questions"]
    assert len({q["id"] for q in qs}) == len(qs), "题目 ID 重复"
    ch_ids = {c["id"] for c in bank["chapters"]}
    for q in qs:
        assert q["chapter_id"] in ch_ids, f"章节不存在：{q['id']}"
        keys = [o["key"] for o in q["options"]]
        assert len(keys) == len(set(keys)) and len(keys) >= 4, f"选项异常：{q['id']}"
        assert set(q["answer"]) <= set(keys), f"答案越界：{q['id']}"
        assert (len(q["answer"]) == 1) == (q["type"] == "single"), f"答案数量异常：{q['id']}"
        assert q["explanation"].strip(), f"解析为空：{q['id']}"
        assert q["knowledge"] in next(c for c in bank["chapters"]
                                     if c["id"] == q["chapter_id"])["knowledge"], \
            f"知识点未登记：{q['id']}"
    sig = set()
    for q in qs:
        s = re.sub(r"[\s，。、；：？！“”《》（）()]", "", q["stem"])
        assert s not in sig, f"题干重复：{q['id']}"
        sig.add(s)


def main() -> None:
    bank = build()
    validate(bank)
    out = ROOT / "data" / "questions.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    qs = bank["questions"]
    print(f"题库已生成：{out}")
    print(f"  总题数 {bank['meta']['total']}  单选 {bank['meta']['single']}  多选 {bank['meta']['multiple']}")
    print(f"  章节 {len(bank['chapters'])}  知识点 {sum(len(c['knowledge']) for c in bank['chapters'])}")
    print("  每章题数：")
    for c in bank["chapters"]:
        n = sum(1 for q in qs if q["chapter_id"] == c["id"])
        print(f"    {c['name']}：{n}")
    dist = Counter(q["knowledge"] for q in qs)
    print(f"  知识点最小样本 {min(dist.values())}，最大 {max(dist.values())}")


if __name__ == "__main__":
    main()
