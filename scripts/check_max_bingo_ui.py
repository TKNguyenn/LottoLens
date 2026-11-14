"""Desktop integration, temporary SQLite and no real source/provider calls."""
import os
import json
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from app.ui import Desktop
from app.gameplay import BINGO_PLAYS, bingo_choices
from check_max_bingo_generation import history
from check_preferences import wait_idle


def main():
    app=QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as directory, patch("app.ai._send") as send, patch("app.ui.OfficialSource.fetch_history") as fetch:
        root=Path(directory); w=Desktop(root/"history.db",root/"config.json")
        try:
            assert hasattr(w,"ticket_controls"), "missing per-game ticket controls"
            w.set_analysis_window(30)
            for game in ("max3d","max3dpro","bingo18"):
                w.game.setCurrentIndex(w.game.findData(game)); rule=w.rule
                w.store.add_draws(rule,history(rule));w.refresh()
                assert w.odds_table.rowCount()>0
                if game=="bingo18":
                    w.change_play("any_triple")
                    assert w.sample_ticket().selections=={"play":"any_triple","main":[]}
                    assert w.ticket_controls[1]["play"].findData("any_triple")==-1
                    assert w.odds_table.rowCount()>0
                contexts=tuple(key for key in BINGO_PLAYS if key!="any_triple") if game=="bingo18" else (None,)
                for context in contexts:
                    if context:
                        group=w.ticket_controls[0]["play"]
                        group.setCurrentIndex(group.findData(context));app.processEvents()
                        # Probability and suggestion selectors are deliberately independent.
                        w.change_suggestion_play(context)
                        assert w.ticket_controls[1]["play"].currentData()==context
                        assert w.count.maximum()==min(100,len(bingo_choices(context)))
                        assert w.sample_ticket().selections["play"]==context
                        choice=w.ticket_controls[0]["choice"]
                        choice.setCurrentIndex(choice.count()-1)
                        assert w.ticket_controls[2]["choice"].currentData()==choice.currentData()
                        assert w.ticket_controls[1]["choice"].isHidden()
                    for method in ("uniform_v1","frequency90_laplace1_v1","bayes90_v1"):
                        w.method.setCurrentIndex(w.method.findData(method));w.count.setValue(1);w.make_suggestions()
                        assert w.generated is not None, w.notice.text()
                        assert w.suggestion_table.rowCount()==1
                        if game=="bingo18": assert w.generated[2][0].selections["play"]==context
                        assert w.odds_table.rowCount()>0
                    w.target.setText("999999");w.save_generated()
                    assert w.store.suggestions(rule)
                    for language in ("en","vi"):
                        w.apply_language(language)
                        for theme in ("light","dark"):
                            w.set_theme(theme);w.resize(1000,700);w.show();app.processEvents()
                            for page in (3,4): w.nav.setCurrentRow(page);app.processEvents()
                if game=="max3dpro":
                    controls=w.ticket_controls[0]
                    controls["first"].setText("999");controls["second"].setText("007")
                    controls["second"].editingFinished.emit()
                    assert w.sample_ticket().selections=={"main":["999","007"]}
                    assert w.ticket_controls[1]["first"].text()=="999"
            w.game.setCurrentIndex(w.game.findData("bingo18"))
            w.change_play("sum");w.change_suggestion_play("sum");w.count.setValue(2)
            w.method.setCurrentIndex(w.method.findData("ai_history90_v1"))
            w.key.setText("qa-temporary-secret")
            text=json.dumps({"tickets":[{"play":"sum","main":[10]},{"play":"sum","main":[11]}],"explanation":"offline fixture"})
            send.return_value={"id":"qa","model":"test","status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":text}]}]}
            w.make_suggestions();wait_idle(w)
            send.assert_called_once()
            assert w.generated and w.generated[4]["play_context"]=="sum",w.notice.text()
            assert len(w.generated[2])==2
            assert json.loads(send.call_args.args[2]["input"])["play_context"]=="sum"
            previous=w.generated,w.explanation.toPlainText()
            w.change_sample({"play":"sum","main":[18]})
            assert previous==(w.generated,w.explanation.toPlainText())
            send.reset_mock()
            from threading import Event
            ready=Event()
            def task(cancel,progress,delta):
                ready.wait(2)
                return {"status":"completed"}
            w.start_task(task,lambda result:None,"test")
            assert all(not c[key].isEnabled() for c in w.ticket_controls for key in ("play","choice","first","second"))
            ready.set();wait_idle(w)
            assert w.ticket_controls[0]["play"].isEnabled()
            send.assert_not_called();fetch.assert_not_called()
        finally:
            w.close()
        from app.storage import Store
        from app.rules import get_rule
        from app.domain import Ticket,validate_ticket
        store=Store(root/"history.db")
        try:
            for game in ("max3d","max3dpro","bingo18"):
                rule=get_rule(game);records=store.suggestions(rule)
                assert records
                for record in records:
                    validate_ticket(rule,Ticket(**record["ticket"]))
                    assert record["metadata"]["history_window"]==30
                    assert "qa-temporary-secret" not in json.dumps(record)
            assert {row["ticket"]["selections"]["play"] for row in store.suggestions(get_rule("bingo18"))}==set(BINGO_PLAYS)-{"any_triple"}
        finally:store.close()
    print("Max/Bingo desktop OK: contexts/samples/limits/generation/save/language/themes/worker locks; offline")


if __name__=="__main__":main()
