"""Hermes-backed quiz gateway. The Server never stores or exposes question data."""
from aiohttp import web
from core.security.session import SessionError
QUIZ_TOOLS={"subjects":"quiz.subjects","next":"quiz.questions.next","answer":"quiz.questions.answer","wrong":"quiz.wrong_answers"}
class QuizHandler:
    def __init__(self,auth,manager_factory): self.auth,self.manager_factory=auth,manager_factory
    def routes(self): return [web.get('/v1/quiz/subjects',self.subjects),web.get('/v1/quiz/questions/next',self.next_question),web.post('/v1/quiz/questions/{id}/answer',self.answer),web.get('/v1/quiz/wrong-answers',self.wrong_answers)]
    def _manager(self,request,scope='quiz:read'):
        try: ctx=self.auth.authenticate(request.headers.get('Authorization'),request.headers.get('Device-Id'),scope)
        except SessionError as exc: raise web.HTTPUnauthorized(text=str(exc)) if exc.status==401 else web.HTTPForbidden(text=str(exc))
        manager=self.manager_factory(ctx)
        if manager is None: raise web.HTTPServiceUnavailable(text='设备当前不在线')
        return getattr(getattr(manager,'func_handler',manager),'tool_manager',manager)
    async def _call(self,request,key,args=None,scope='quiz:read'):
        manager=self._manager(request,scope)
        try: result=await manager.execute_tool(QUIZ_TOOLS[key],args or {})
        except Exception as exc: raise web.HTTPBadGateway(text='题库服务不可用') from exc
        return web.json_response({'code':0,'msg':'success','data':getattr(result,'content',result)})
    async def subjects(self,request): return await self._call(request,'subjects')
    async def next_question(self,request): return await self._call(request,'next',dict(request.query))
    async def answer(self,request):
        body=await request.json(); body['question_id']=request.match_info['id']; return await self._call(request,'answer',body,'quiz:write')
    async def wrong_answers(self,request): return await self._call(request,'wrong')
