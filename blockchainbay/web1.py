import os,web
import urllib.parse
from web.httpserver import StaticMiddleware

class MyStaticMiddleware(StaticMiddleware):
    def __init__(self, app, prefix='/data/static/'):
        StaticMiddleware.__init__(self, app, prefix)


urls = ('/', 'index',
        '/description','description',
        '/res/(.*)','static'
        )
srvpath=os.path.dirname(os.path.realpath(__file__))
render = web.template.render('%s/data/templates/' % srvpath)
my_form = web.form.Form(web.form.Textbox('', class_='textfield', id='textfield'))

class static:
    def GET(self, media):
        try:
            f = open('%s/data/static/%s' % (srvpath,media), 'r')
            return f.read()
        except:
            return '' # you can send an 404 error here if you want

class index:
    listStart='<ol id="torrents" class="view-single">'
    listHeader=('<li class="list-header">'

                '<span class="list-item list-header item-name"><label>Name</label></span>'
                '<span class="list-item list-header item-size"><label>Size</label></span>'
                '<span class="list-item list-header item-seed"><label>Seeders</label></span>'
                '<span class="list-item list-header item-leech"><label>Leechers</label></span>'
                '<span class="list-item list-header item-user"><label>Votes</label></span>'
                '</li>')
    listEntry=('<li class="list-entry %s">'
               '<span class="list-item item-name item-title"><label><a href="/description?id=%s">%s</a></label></span>'
               '<span class="list-item item-size"><label>%d</lable></span>'
               '<span class="list-item item-seed"><label>%d</lable></span>'
               '<span class="list-item item-leech"><label>%d</lable></span>'
               '<span class="list-item item-user"><label>%d</lable></span>'
               '</li>')
    def GET(self):
        form = my_form()
        return render.index(form, "",data.logo)

    def POST(self):
        form = my_form()
        form.validates()
        #s = contract.functions.getMagnetCount().call()
           #---Do cached search of substings
        cmd = form.value['textfield']
        resultStr=self.listStart+self.listHeader
        if len(cmd)>2:
            fcount=0
            index=-1
            for i in data.cache:
                index+=1
                try:
                  if i.name.lower().find(cmd.lower().encode('utf-8'))>=0:
                    fcount+=1
                    alt=""
                    if (fcount%2==0): alt="alt"
                    resultStr+=self.listEntry % (alt,index,i.name.decode(),i.size_bytes,i.seeders,i.leechers,i.vote)
                except Exception as e:
                    pass
        if (fcount==0): resultStr+="<h2>NO RESULTS</H2>"
        resultStr+='</ol>'
        return resultStr

class description(index):
    def GET(self):
        i = int(web.input(id=None).id)
        if ((i>=0) and (i<=len(data.cache))):
            form = my_form()
            return render.detail(form,data.logo,
                                 data.cache[i].name.decode(),
                                 data.cache[i].size_bytes,
                                 data.cache[i].created_unix,
                                 data.cache[i].seeders,
                                 data.cache[i].leechers,
                                 data.cache[i].infohash.decode().upper(),
                                 data.config['link'] % (urllib.parse.quote(data.cache[i].infohash.decode()),urllib.parse.quote(data.cache[i].name.decode()))
                                 ,"")

def web1(dat):
    global data
    data = dat
    app = web.application(urls, globals())
    web.httpserver.runsimple(app.wsgifunc(), ("localhost", 8888))
    app.run(MyStaticMiddleware)
