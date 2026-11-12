"""New-game generator/AI safety checks with temporary data and mocked transport."""
import json
import sys
from pathlib import Path
from random import Random
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import ai
from app.ai_generation import build_generation_request, generate_with_ai, parse_tickets
from app.domain import Draw, canonical, validate_ticket
from app.generation import METHODS, explain_ticket, generate, generation_profile
from app.gameplay import BINGO_PLAYS, bingo_choices
from app.rules import get_rule


def history(rule, n=90):
    records=[]
    for i in range(n):
        if rule.kind=="triples":
            groups={}; offset=0
            for name,size in (("special",2),("first",4),("second",6),("third",8)):
                groups[name]=[f"{(i*7+j+offset)%1000:03}" for j in range(size)];offset+=size
            payload={"groups":groups}
        else: payload={"main":[i%6+1,(i+1)%6+1,(i+2)%6+1]}
        records.append(Draw(rule.game_id,rule.mode_id,rule.rule_version,str(i+1),
            f"2026-10-{i//24+1:02}T{i%24:02}:00:00+00:00",payload,"https://example.test/", "2026-11-01T00:00:00+00:00","a"*64))
    return records


def check():
    config=ai.AIConfig(api_key="test-secret")
    for game in ("max3d","max3dpro","bingo18"):
        rule=get_rule(game); draws=history(rule)
        contexts=BINGO_PLAYS if game=="bingo18" else (None,)
        for context in contexts:
            for method in METHODS:
                count=1 if context=="any_triple" else 3
                tickets=generate(rule,draws,count,method,Random(42),history_window=30,play_context=context)
                assert len(tickets)==count and len({canonical(t.selections) for t in tickets})==count
                for t in tickets: validate_ticket(rule,t)
                detail=explain_ticket(rule,draws,tickets[0],method,history_window=30,play_context=context)
                assert detail["history_window"]==30 and detail["history_used"]==30
                assert detail["cutoff_draw_id"]=="90"
            if context:
                capacity=len(bingo_choices(context))
                assert len(generate(rule,[],capacity,"uniform_v1",Random(1),play_context=context))==capacity
                try: generate(rule,[],capacity+1,"uniform_v1",Random(1),play_context=context)
                except ValueError: pass
                else: raise AssertionError("capacity")
            sample=generate(rule,draws,1,"bayes90_v1",Random(2),history_window=30,play_context=context)[0].selections
            parsed,_=parse_tickets(json.dumps({"tickets":[sample],"explanation":"ok"}),rule,1,play_context=context)
            assert parsed[0].selections==sample
            if game=="bingo18":
                other="sum" if context!="sum" else "single"
                try: parse_tickets(json.dumps({"tickets":[bingo_choices(other)[0]],"explanation":"x"}),rule,1,play_context=context)
                except ValueError: pass
                else: raise AssertionError("AI changed play")
            _,_,body=build_generation_request(config,rule,draws,1,history_window=30,play_context=context)
            request=json.loads(body["input"])
            assert len(request["history"])==30 and len(body["input"])<=10_000
            assert request["play_context"]==context
            assert "test-secret" not in body["input"]
            raw={"id":"r1","model":"test","status":"completed","output":[{"type":"message","content":[{"type":"output_text","text":json.dumps({"tickets":[sample],"explanation":"ok"})}]}]}
            with patch("app.ai._send",return_value=raw) as send:
                result=generate_with_ai(config,rule,draws,1,history_window=30,play_context=context)
                send.assert_called_once()
                assert result["metadata"]["history_window"]==30
                assert result["metadata"]["play_context"]==context
                assert "test-secret" not in canonical(result["metadata"])
            with patch("app.ai._send",side_effect=ValueError("failure")) as send:
                try: generate_with_ai(config,rule,draws,1,history_window=30,play_context=context)
                except ValueError: pass
                else: raise AssertionError("retry")
                send.assert_called_once()
            with patch("app.ai._send") as send:
                try: generate_with_ai(config,rule,draws[:10],1,history_window=30,play_context=context)
                except ValueError: pass
                else: raise AssertionError("insufficient")
                send.assert_not_called()
        if game.startswith("max"):
            t={"main":["007","001"] if game=="max3dpro" else ["007"]}
            assert parse_tickets(json.dumps({"tickets":[t],"explanation":"ok"}),rule,1)[0][0].selections==t
            _,_,body=build_generation_request(config,rule,draws,1)
            assert len(json.loads(body["input"])["history"])==90
            assert len(body["input"])<=10_000
            with patch("app.ai._send") as send:
                try: generate_with_ai(config,rule,history(rule,200),1,history_window=200)
                except ValueError as error: assert "10.000" in str(error)
                else: raise AssertionError("oversize AI not blocked")
                send.assert_not_called()
    print("Max/Bingo generation OK: all methods/contexts, finite capacity, N, AI typing/order/no retry/secrets")


if __name__=="__main__": check()
