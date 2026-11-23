# -*- coding: utf-8 -*-
"""端到端自测：模式切换、判分、统计、错题本、筛选、持久化、全题渲染。

运行：.venv\\Scripts\\python.exe tests\\smoke_test.py
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.main_window import MainWindow  # noqa: E402
from app.models import load_bank  # noqa: E402
from app.store import ProgressStore  # noqa: E402
from app.ui import theme  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def ok(msg):
    print(f"  ✓ {msg}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(theme.base_font(10))
    app.setStyleSheet(theme.qss())

    p = Path(__file__).parent / "_smoke_progress.json"
    if p.exists():
        p.unlink()
    bank = load_bank(ROOT / "data" / "questions.json")
    store = ProgressStore(p)
    w = MainWindow(bank, store)
    w.show()
    app.processEvents()

    print("[0] 记录文件位置")
    from app.__main__ import _state_path
    state = _state_path()
    assert str(state).startswith(str(ROOT)), state
    assert state.parent.name == "userdata", state
    ok(f"记录保存在程序目录：{state.relative_to(ROOT)}")

    print("[1] 初始状态")
    assert w.session.total == 271
    assert w.session.stats().attempted == 0
    ok("随机模式队列 271 题")

    print("[2] 首题答对")
    q = w.session.current
    for k in sorted(q.answer):
        w.view.toggle_key(k)
    w.view.submit()
    app.processEvents()
    st = w.session.stats()
    assert (st.attempted, st.correct, st.wrong) == (1, 1, 0), st
    ok(f"统计 1/1，正确率 {st.accuracy:.0%}")

    print("[3] 多选少选判错")
    w._on_next()
    q2 = w.session.current
    while not q2.is_multiple:
        w._on_next()
        q2 = w.session.current
    pick = sorted(q2.answer)[: max(1, len(q2.answer) - 1)]
    for k in pick:
        w.view.toggle_key(k)
    w.view.submit()
    app.processEvents()
    st = w.session.stats()
    assert st.wrong == 1, st
    assert q2.id in w.session.wrong_ids()
    ok(f"少选判错，错题本 {len(w.session.wrong_ids())} 题")

    print("[4] 切换模式保留统计与错题")
    before = w.session.stats()
    w._switch_mode("filter")
    app.processEvents()
    w._switch_mode("wrong")
    app.processEvents()
    after = w.session.stats()
    assert (before.attempted, before.correct, before.wrong) == (after.attempted, after.correct, after.wrong)
    assert set(w.session.wrong_ids()) == {q2.id}
    ok("三种模式来回切换，统计与错题记录不变")

    print("[5] 错题模式重新作答并移出错题本")
    assert w.session.total == 1 and w.session.current.id == q2.id
    assert w.stack.currentIndex() == 0
    for k in sorted(q2.answer):
        w.view.toggle_key(k)
    w.view.submit()
    app.processEvents()
    assert w.session.stats().wrong == 0
    assert w.session.wrong_ids() == []
    ok("答对后自动移出错题本")

    print("[6] 筛选：章节 + 题型")
    w._switch_mode("filter")
    w.sidebar.chapter_select.set_value("06")
    w.sidebar._on_chapter(None)
    w.sidebar.type_select.set_value("multiple")
    w._on_filters()
    app.processEvents()
    assert w.session.total == 7, w.session.total
    assert all(q.chapter_id == "06" and q.is_multiple
               for q in (bank.by_id[i] for i in w.session.queue))
    ok("第六章 + 多选 = 7 题")

    print("[7] 知识点筛选")
    kp_items = [v for v, _ in w.sidebar.kp_select._items if v]
    assert kp_items
    w.sidebar.kp_select.set_value(kp_items[0])
    w._on_filters()
    app.processEvents()
    assert all(bank.by_id[i].knowledge == kp_items[0] for i in w.session.queue)
    ok(f"知识点「{kp_items[0]}」= {w.session.total} 题")

    print("[8] 空筛选结果")
    w.sidebar.kp_select.set_value(None)
    w.sidebar.chapter_select.set_value("01")
    w.sidebar._on_chapter(None)
    w.sidebar.type_select.set_value("multiple")
    w.sidebar.kp_select.set_value("社会主要矛盾")
    w._on_filters()
    app.processEvents()
    if w.session.total == 0:
        assert w.stack.currentIndex() == 1
        ok("无结果时展示空状态页")
    else:
        ok(f"该组合有 {w.session.total} 题（跳过空状态断言）")

    print("[9] 重启后进度仍在")
    w._flush()
    store2 = ProgressStore(p)
    assert len(store2.records) == 2
    ok("进度文件落盘，重新加载后 2 条记录")

    print("[10] 全题渲染")
    w._switch_mode("filter")
    w.sidebar.chapter_select.set_value(None)
    w.sidebar._on_chapter(None)
    w.sidebar.kp_select.set_value(None)
    w.sidebar.type_select.set_value(None)
    w._on_filters()
    app.processEvents()
    assert w.session.total == 271
    for i in range(271):
        w.session.index = i
        w._render()
        app.processEvents()
    ok("271 题逐题渲染无异常")

    print("[11] 主题切换与持久化")
    from app.ui import theme as th
    assert th.mode() == "light", th.mode()
    w._toggle_theme()
    app.processEvents()
    assert th.mode() == "dark"
    assert "background: #0D1320" in app.styleSheet() or "#0D1320" in app.styleSheet()
    w._toggle_theme()
    app.processEvents()
    assert th.mode() == "light"
    w._toggle_theme()
    app.processEvents()
    w._flush()
    assert ProgressStore(p).get_pref("theme") == "dark"
    ok("明暗切换正常，选择写入偏好")
    w._toggle_theme()
    app.processEvents()

    print("[12] 名词解释命中")
    from app.glossary import match_terms
    hit = [t for t, _ in match_terms(bank.by_id["09S02"], bank.glossary)]
    assert "十一个坚持" in hit, hit
    assert len(bank.glossary) >= 30
    ok(f"术语表 {len(bank.glossary)} 条，命中：{hit}")

    print("[13] 随机模式的题型范围")
    w._switch_mode("random")
    w.sidebar.type_select.set_value("single")
    w._on_filters()
    app.processEvents()
    assert w.session.total == 176, w.session.total
    assert all(bank.by_id[i].type == "single" for i in w.session.queue)
    w.sidebar.type_select.set_value("multiple")
    w._on_filters()
    assert w.session.total == 95, w.session.total
    ok("随机模式可限定单选（176）/ 多选（95）")
    w.sidebar.type_select.set_value(None)
    w._on_filters()

    print("[14] 出题优先级")
    import random as _random
    from app import priority

    w.store.reset()
    # 覆盖不同知识点各取一题
    seen_kp, sample = set(), []
    for q in bank.questions:
        if q.knowledge not in seen_kp:
            seen_kp.add(q.knowledge)
            sample.append(q)
        if len(sample) >= 5:
            break
    weak, solid, untouched = sample[0], sample[1], sample[2]
    for _ in range(2):
        w.store.record(weak.id, sorted(weak.answer), False)
    for _ in range(3):
        w.store.record(solid.id, sorted(solid.answer), True)

    m_weak = priority.mastery(w.store.get(weak.id))
    m_solid = priority.mastery(w.store.get(solid.id))
    assert m_weak < 0.4 and m_solid > 0.75, (m_weak, m_solid)
    assert priority.mastery(None) is None
    ok(f"掌握度：错两次 {m_weak:.0%} / 连对三次 {m_solid:.0%} / 未做 None")

    pool = [weak, solid, untouched] + sample[3:]
    ordered = priority.order(pool, w.store.records, bank, _random.Random(7))
    assert ordered[0].id in {weak.id, untouched.id}, ordered[0].id
    assert ordered[-1].id == solid.id, [q.id for q in ordered]
    ok(f"排序：薄弱题在前、已掌握题殿后（{ordered[0].id} → {ordered[-1].id}）")

    # 同一知识点不连出：给同知识点的两题都设成薄弱，第三题来自别的知识点
    pair = [q for q in bank.questions if q.knowledge == weak.knowledge][:2]
    other = next(q for q in bank.questions
                 if q.knowledge != weak.knowledge and q.id != solid.id)
    for q in pair:
        w.store.record(q.id, sorted(q.answer), False)
    trio = priority.order(pair + [other], w.store.records, bank, _random.Random(3))
    assert not (trio[0].knowledge == trio[1].knowledge == pair[0].knowledge), \
        [q.id for q in trio]
    ok("知识点分散：同一知识点不会连续出现")

    # 记录里不再有按时间安排的字段
    rec = w.store.get(weak.id)
    assert "due" not in rec and "recent" in rec
    assert w.session.weak_count() >= 2
    ok(f"记录无时间字段，待巩固 {w.session.weak_count()} 题")

    print("[15] 字号三档")
    w._set_font_level("large")
    app.processEvents()
    big = f"{round(13 * theme.FONT_SCALES['large'], 1)}pt"
    assert theme.font_level() == "large" and big in app.styleSheet(), big
    w._flush()
    assert ProgressStore(p).get_pref("font_scale") == "large"
    w._set_font_level("small")
    small = f"{round(13 * theme.FONT_SCALES['small'], 1)}pt"
    assert small in app.styleSheet(), small
    w._set_font_level("medium")
    ok("大 / 中 / 小切换生效并写入偏好")

    print("[16] 打乱与重新开始")
    cur = w.session.current
    if cur.id not in w.session.round_done:
        for k in sorted(cur.answer):
            w.view.toggle_key(k)
        w.view.submit()
    app.processEvents()
    assert cur.id in w.session.round_done and w.view.feedback.isVisible()
    before = list(w.session.queue[:8])
    w._shuffle()
    app.processEvents()
    assert w.session.index == 0 and w.session.queue[:8] != before
    assert w.view.feedback.isVisible() is False or w.session.queue[0] == cur.id
    ok("R 键真正打乱队列并回到第一题")

    w._restart_round()
    app.processEvents()
    assert not w.session.round_done
    assert not w.view.feedback.isVisible() and w.view.placeholder.isVisible()
    assert w.session.stats().attempted >= 1
    ok("重新开始本轮清空作答状态，统计保留")

    print("[17] 快捷键与打乱按钮")
    from PySide6.QtCore import Qt as _Qt
    from PySide6.QtTest import QTest
    w.activateWindow()
    app.processEvents()
    w.session.index = 0
    w._render()
    app.processEvents()
    QTest.keyClick(w, _Qt.Key_B)
    app.processEvents()
    assert "B" in w.view._chosen, w.view._chosen
    before = list(w.session.queue[:6])
    QTest.keyClick(w, _Qt.Key_R)
    app.processEvents()
    assert w.session.queue[:6] != before
    ok("A–E 选选项、R 打乱队列都生效")

    w.session.round_done.add("dummy")
    before = list(w.session.queue[:6])
    w.sidebar.shuffle_btn.click()
    app.processEvents()
    assert not w.session.round_done and w.session.index == 0
    assert w.session.queue[:6] != before
    ok("侧栏「打乱并重新开始」清空本轮并重排")

    print("[18] 重置")
    w.store.reset()
    w.session.rebuild(keep_current=False)
    w._refresh_all()
    app.processEvents()
    assert w.session.stats().attempted == 0 and w.session.wrong_ids() == []
    ok("重置后统计与错题清空")

    w.close()
    if p.exists():
        p.unlink()
    print("\n全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
