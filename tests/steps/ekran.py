"""Duman testi: ekran görüntüleri (en son)."""
import os


from smoke_base import step, _pump


@step("ekran görüntüleri")
def _shots(ctx):
    shots, win, app = ctx["shots"], ctx["win"], ctx["app"]
    if not shots:
        return
    from erk.theme import theme
    win.toast_w.hide()
    for th in ("amoled", "white"):
        theme.apply(th)
        for key in win.pages:
            win.show_page(key)
            _pump(app, 6)
            win.grab().save(os.path.join(shots, f"{th}_{key}.png"))
    theme.apply("amoled")
    from erk.forms import FormDialog
    d = FormDialog(win, ctx["store"], "exams", ctx["store"].all("exams")[1])
    d.show()
    _pump(app, 6)
    d.grab().save(os.path.join(shots, "form_exam.png"))
    d.close()
    d = FormDialog(win, ctx["store"], "routine", ctx["store"].all("routine")[0])
    d.show()
    _pump(app, 6)
    d.grab().save(os.path.join(shots, "form_routine.png"))
    d.close()
