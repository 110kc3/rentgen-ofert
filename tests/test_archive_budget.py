"""Archive maintenance cannot consume the current-offer pass or lose its cursor."""
import json
import copy
import pytest
from scraper import nieruchomosci_online as nol, coverage


class Clock:
    now=0
    def monotonic(self): return self.now
    def sleep(self,seconds): self.now+=seconds


def offer(i, archived=False):
    return {'url':f'https://katowice.nieruchomosci-online.pl/x/{i}.html',
            'availability':'OutOfStock' if archived else 'InStock',
            'price':'400000','itemOffered':{'floorSize':{'value':50}}}


class Pages:
    def __init__(self,pages,clock=None,fail=None):
        self.pages=pages;self.clock=clock;self.fail=fail;self.calls=[]
    def get(self,url,**kwargs):
        page=int(url.split('?p=')[-1]) if '?p=' in url else 1
        self.calls.append((url,page,kwargs['timeout']))
        if self.clock:self.clock.now+=1
        if self.fail==page:raise OSError('fixture interruption')
        class Response:
            status_code=200
            text=json.dumps(self.pages.get(page,[]))
            def raise_for_status(self):pass
        return Response()


def run(monkeypatch,clock,archive,state=None,budget=1,towns=None,region='slaskie'):
    monkeypatch.setattr(nol,'extract_offers',json.loads)
    monkeypatch.setattr(nol.time,'monotonic',clock.monotonic)
    monkeypatch.setattr(nol.time,'sleep',clock.sleep)
    current=Pages({1:[offer(1)],2:[offer(10,True)],3:[offer(11,True)]})
    result=nol.scrape(max_pages=20,delay=0,session=current,archive_session=archive,
        types=('flat',),towns=towns or {'katowice':'Katowice'},region=region,
        harvest_archive=True,archive_state=state,archive_budget_s=budget,
        today='2026-09-29',log=lambda *a:None)
    return result,current,nol.scrape.last_archive_state


def test_budget_resume_and_completed_cadence(monkeypatch):
    clock=Clock();pages={2:[offer(10,True)],3:[offer(11,True)],4:[]}
    old={'schema':1,'refreshed':'2026-09-18','records':99,'by_type':{'flat':{'archived':99}}}
    original=copy.deepcopy(old)
    rows,current,state=run(monkeypatch,clock,Pages(pages,clock),old)
    assert [r['source_id'] for r in rows]==['1','10']
    assert len(current.calls)==3 and state['cycle']['pending'][0]['page']==3
    assert state['refreshed']=='2026-09-18' and old==original
    assert nol.archive_due(state,'2026-09-29','auto')
    summary=coverage.summarise(nol.scrape.last_coverage,listings=rows)['by_source']['nieruchomosci-online']
    assert summary['current']==1 and summary['archived']==1
    assert summary['archive_harvest']['mode']=='partial'
    assert summary['archive_harvest']['pending']==1
    rows,_,state=run(monkeypatch,clock,Pages(pages,clock),state,budget=2)
    assert {r['source_id'] for r in rows}=={'1','11'}
    assert 'cycle' not in state and state['complete']
    assert state['records']==2 and state['refreshed']=='2026-09-29'
    assert not nol.archive_due(state,'2026-09-30','auto')


def test_failed_page_keeps_cursor_and_does_not_block_other_towns(monkeypatch):
    clock=Clock();archive=Pages({},clock,fail=2)
    _,_,state=run(monkeypatch,clock,archive,budget=20,towns={'katowice':'Katowice','gliwice':'Gliwice'})
    assert len(archive.calls)==2
    assert {t['page'] for t in state['cycle']['pending']}=={2}
    assert len(state['cycle']['errors'])==2 and 'refreshed' not in state


def test_current_id_never_reappears_as_duplicate_archive_url(monkeypatch):
    clock=Clock()
    rows,_,_=run(monkeypatch,clock,Pages({2:[offer(1,True),offer(10,True)]},clock))
    assert [r['source_id'] for r in rows]==['1','10']


def test_region_checkpoint_cannot_leak_and_skip_preserves_progress(monkeypatch):
    state={'schema':2,'region':'opolskie','cycle':{'pending':[{'page':5}]}}
    with pytest.raises(ValueError,match='another region'):
        run(monkeypatch,Clock(),Pages({}),state)
    assert not nol.archive_due(state,'2026-09-29','skip')


def test_corrupt_checkpoint_is_not_silently_reset(tmp_path):
    path=tmp_path/'state.json';path.write_text('{bad')
    with pytest.raises(ValueError):nol.load_archive_state(path)
    path.write_text(json.dumps({'schema':99}))
    with pytest.raises(ValueError):nol.load_archive_state(path)


def test_time_remaining_bounds_request_timeout(monkeypatch):
    clock=Clock();archive=Pages({2:[offer(10,True)]},clock)
    run(monkeypatch,clock,archive,budget=0.5)
    assert archive.calls[0][2]==0.5
    assert len(archive.calls)==1


def test_duplicate_page_end_is_finite(monkeypatch):
    clock = Clock()
    pages = {2:[offer(10,True)],3:[offer(10,True)],4:[offer(10,True)]}
    archive = Pages(pages,clock)
    rows,_,state = run(monkeypatch,clock,archive,budget=10)
    assert len(archive.calls) == 3
    assert state['complete'] and state['records'] == 1
    assert [r['source_id'] for r in rows] == ['1','10']


def test_failure_after_progress_resumes_failed_page(monkeypatch):
    clock = Clock()
    archive = Pages({2:[offer(10,True)]},clock,fail=3)
    rows,_,state = run(monkeypatch,clock,archive,budget=10)
    assert state['cycle']['pending'][0]['page'] == 3
    assert state['cycle']['seen']['flat'] == ['10']
    assert [r['source_id'] for r in rows] == ['1','10']
    archive = Pages({3:[offer(11,True)]},clock)
    rows,_,state = run(monkeypatch,clock,archive,state,budget=10)
    assert archive.calls[0][1] == 3
    assert state['complete'] and state['records'] == 2


@pytest.mark.parametrize('budget', [0, -1, float('inf'), float('nan')])
def test_invalid_budget_fails_before_current_requests(monkeypatch,budget):
    with pytest.raises(ValueError,match='budget'):
        run(monkeypatch,Clock(),Pages({}),budget=budget)
