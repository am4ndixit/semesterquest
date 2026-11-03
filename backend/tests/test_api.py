from app import engines
from .conftest import login


def test_health_and_route_surface(client):
    assert client.get('/api/health').json()['ok'] is True
    assert len(client.get('/openapi.json').json()['paths']) >= 25
    assert client.get('/').status_code == 200
    assert client.get('/assets/app.js').status_code == 200
    assert client.get('/assets/styles.css').status_code == 200


def test_adypu_auth_and_otp(client):
    bad=client.post('/api/auth/start',json={'email':'student@gmail.com','password':'password123'})
    assert bad.status_code==400
    short=client.post('/api/auth/start',json={'email':'e26b07f0008@adypu.edu.in','password':'short'})
    assert short.status_code==422
    h=login(client,'e26b07f0009@adypu.edu.in')
    assert client.get('/api/me',headers=h).status_code==200
    assert client.get('/api/me').status_code==401


def test_theme_and_worlds(client,auth):
    assert len(client.get('/api/worlds',headers=auth).json())==3
    assert client.patch('/api/me/theme',headers=auth,json={'theme':'dark'}).json()['theme']=='dark'
    assert client.patch('/api/me/theme',headers=auth,json={'theme':'pink'}).status_code==422


def test_quiz_grading_and_idempotent_xp(client,auth):
    q=client.get('/api/quiz/questions?world=maths',headers=auth).json()[0]
    answer=q['options'].index('16')
    first=client.post('/api/quiz/answer',headers=auth,json={'question_id':q['id'],'selected':answer}).json()
    second=client.post('/api/quiz/answer',headers=auth,json={'question_id':q['id'],'selected':answer}).json()
    assert first['correct'] and first['xp']==10
    assert second['correct'] and second['xp']==0 and second['already_mastered']
    assert client.get('/api/dashboard',headers=auth).json()['user']['xp'] >= 10


def test_python_runner_fails_closed_without_docker(client,auth,monkeypatch):
    monkeypatch.setattr(engines.shutil,'which',lambda _:None)
    result=client.post('/api/python/run',headers=auth,json={'source':'print(42)'}).json()
    assert result['error']['type']=='SandboxUnavailable'
    assert 'No code was executed' in result['stderr']


def test_virtual_shell_and_git(client,auth):
    r=client.post('/api/shell/run',headers=auth,json={'command':'grep -i error practice/log.txt | head -1'}).json()
    assert 'ERROR database timeout' in r['stdout']
    r=client.post('/api/shell/run',headers=auth,json={'command':'mkdir -p quest/src && touch quest/README.md quest/src/main.py quest/run.sh && chmod +x quest/run.sh'}).json()
    assert r['exit']==0
    checked=client.post('/api/shell/missions/sh-01/check',headers=auth).json()
    assert checked['cleared'] and checked['xp']==40
    client.post('/api/shell/run',headers=auth,json={'command':'git init && git add . && git commit -m "first quest"'})
    assert client.post('/api/shell/missions/sh-03/check',headers=auth).json()['cleared']
    client.post('/api/shell/run',headers=auth,json={'command':'grep ERROR practice/log.txt > error_report.txt && grep -c ERROR practice/log.txt > error_count.txt'})
    assert client.post('/api/shell/missions/sh-02/check',headers=auth).json()['cleared']
    assert client.post('/api/shell/missions/sh-05/check',headers=auth).json()['cleared']
    dangerous=client.post('/api/shell/run',headers=auth,json={'command':'rm -rf ~'}).json()
    assert 'refusing' in dangerous['stderr']
    forbidden=client.post('/api/shell/run',headers=auth,json={'command':'curl http://example.com'}).json()
    assert 'command not found' in forbidden['stderr']


def test_upload_retrieval_and_flashcards(client,auth):
    text=('Operating Systems lecture notes\n\nDeadlock is a condition in which processes wait forever for resources held by one another. '
          'The four necessary conditions are mutual exclusion, hold and wait, no preemption, and circular wait.\n\n'
          'A process is a program in execution with its own address space. Scheduling selects which process gets CPU time.')
    up=client.post('/api/materials',headers=auth,files={'file':('os_lecture.txt',text,'text/plain')},data={'kind':'notes'})
    assert up.status_code==200, up.text
    mid=up.json()['id']
    tutor=client.post('/api/tutor',headers=auth,json={'message':'Explain deadlock'}).json()
    assert tutor['grounded'] is True and 'os_lecture.txt' in tutor['cites'][0]['filename']
    generated=client.post('/api/flashcards/generate',headers=auth,json={'material_id':mid})
    assert generated.status_code==200 and generated.json()['created']>=1
    cards=client.get('/api/flashcards',headers=auth).json()
    reviewed=client.post(f"/api/flashcards/{cards[0]['id']}/review",headers=auth,json={'grade':5})
    assert reviewed.status_code==200 and reviewed.json()['interval']>=1


def test_planner_and_cgpa_custom_scale(client,auth):
    task=client.post('/api/planner',headers=auth,json={'title':'Revise process scheduling','subject':'S&AI','due_date':'2026-11-10','priority':'high'}).json()
    assert task['title']=='Revise process scheduling'
    assert client.patch(f"/api/planner/{task['id']}",headers=auth,json={'done':True}).json()['done'] is True
    assert client.get('/api/performance/cgpa',headers=auth).json()['configured'] is False
    scale={'bands':[{'min':0,'gp':0,'label':'F'},{'min':50,'gp':5,'label':'C'},{'min':60,'gp':6,'label':'B'},{'min':70,'gp':7,'label':'B+'},{'min':80,'gp':8,'label':'A'},{'min':90,'gp':9,'label':'A+'}],'target_cgpa':9}
    assert client.put('/api/settings/grade-scale',headers=auth,json=scale).status_code==200
    client.post('/api/courses',headers=auth,json={'name':'PSP','credits':4,'percentage':82})
    result=client.get('/api/performance/cgpa',headers=auth).json()
    assert result['cgpa']==8.0


def test_material_is_private(client,auth):
    other=login(client,'e26b07f0008@adypu.edu.in')
    up=client.post('/api/materials',headers=auth,files={'file':('my_notes.txt','This is a private study note with enough text to retrieve.','text/plain')})
    mid=up.json()['id']
    assert client.delete(f'/api/materials/{mid}',headers=other).status_code==404
