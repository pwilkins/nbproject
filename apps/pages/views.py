# Create your views here.
from django.shortcuts import render_to_response
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.template import TemplateDoesNotExist
import  urllib, json, base64, logging 
from base import auth, signals, annotations, utils_response as UR, models as M
from django.conf import settings
import string, random, forms
from random import choice
from django.core.mail.message import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import escape

id_log = "".join([ random.choice(string.ascii_letters+string.digits) for i in xrange(0,10)])
logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(message)s', filename='/tmp/nb_pages_%s.log' % ( id_log,), filemode='a')
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User

def on_serve_page(sender, **payload): 
    req = payload["req"]
    uid = payload["uid"]
    #print req.META
    #uid =  UR.getUserInfo(req, True)["id"]
    p={}
    p["client"] = req.META.get("REMOTE_HOST", None)
    p["ip"]     = req.META.get("REMOTE_ADDR", None)
    p["referer"]= req.META.get("HTTP_REFERER", None)
    p["path"]   = req.get_full_path()
    annotations.page_served(uid, p)
if settings.MONITOR.get("PAGE_SERVED", False): 
    signals.page_served.connect(on_serve_page, weak=False)


def __extra_confkey_getter(req): 
    if req.user.is_authenticated(): 
        try: 
            o = M.User.objects.get(email=req.user.email)
            return o.confkey
        except M.User.DoesNotExist: 
            return None
    return None

def __serve_page(req, tpl, allow_guest=False, nologin_url=None, mimetype=None): 
    """Serve the template 'tpl' if user is in DB or allow_guest is True. If not, serve the welcome/login screen"""
    o           = {} #for template
    user       = UR.getUserInfo(req, allow_guest, __extra_confkey_getter)
    if user is None:
        redirect_url = nologin_url if nologin_url is not None else ("/login?next=%s" % (req.META.get("PATH_INFO","/"),))
        return HttpResponseRedirect(redirect_url)
    if user.guest is False and (user.firstname is None or user.lastname is None): 
        return HttpResponseRedirect("/enteryourname?ckey=%s" % (user.confkey,)) 
    user = UR.model2dict(user, {"ckey": "confkey", "email": None, "firstname": None, "guest": None, "id": None, "lastname": None, "password": None, "valid": None}) 
    signals.page_served.send("page", req=req, uid=user["id"])

    r = render_to_response(tpl, {"o": o}, mimetype=('application/xhtml+xml' if mimetype is None else mimetype))
    r.set_cookie("userinfo", urllib.quote(json.dumps(user)), 1e6)

    return r

def index(req): 
    return __serve_page(req, settings.DESKTOP_TEMPLATE, False, "/welcome", mimetype="text/html" )
   
def collage(req): 
    return __serve_page(req, settings.COLLAGE_TEMPLATE, mimetype="text/html")

def dev_desktop(req, n): 
    return __serve_page(req, settings.DEV_DESKTOP_TEMPLATE % (n,))

def source(req, n, allow_guest=False):
    source = M.Source.objects.get(pk=n)
    if source.type==M.Source.TYPE_YOUTUBE: 
        return __serve_page(req, settings.YOUTUBE_TEMPLATE, allow_guest , mimetype="text/html")
    elif source.type==M.Source.TYPE_HTML5:
        return HttpResponseRedirect(M.HTML5Info.objects.get(source=source).url)
    else:
        return __serve_page(req, settings.SOURCE_TEMPLATE, allow_guest, mimetype="text/html")
    

def your_settings(req): 
    return __serve_page(req, 'web/your_settings.html', mimetype="text/html")

def embedopenid(req): 
    return __serve_page(req, 'web/embedopenid.html', mimetype="text/html")


def draft(req, tplname):
    try:
        r = render_to_response("drafts/%s.html" % tplname, {}, mimetype='application/xhtml+xml')
        return r
    except TemplateDoesNotExist:
        raise Http404()
 
def newsite(req):
    import base.models as M, random, string 
    form                = None
    auth_user           = UR.getUserInfo(req)
    ensemble_form       = None
    user_form           = None
    if auth_user is not None: 
        return HttpResponseRedirect("/admin")
    if req.method == 'POST':
        user            = M.User(confkey="".join([choice(string.ascii_letters+string.digits) for i in xrange(0,32)]))
        ensemble        = M.Ensemble()
        user_form       = forms.UserForm(req.POST, instance=user)
        ensemble_form   = forms.EnsembleForm(req.POST, instance=ensemble)
        if user_form.is_valid() and ensemble_form.is_valid():             
            user_form.save()
            ensemble.invitekey =  "".join([ random.choice(string.ascii_letters+string.digits) for i in xrange(0,50)])      
            ensemble_form.save()
            m = M.Membership(user=user, ensemble=ensemble, admin=True)
            m.save()
            p = {"tutorial_url": settings.GUEST_TUTORIAL_URL, "conf_url": "http://%s?ckey=%s" %(settings.NB_SERVERNAME, user.confkey), "firstname": user.firstname, "email": user.email, "password": user.password }
            email = EmailMessage(
                "Welcome to NB, %s" % (user.firstname),
                render_to_string("email/confirm_newsite", p), 
                settings.EMAIL_FROM, 
                (user.email, ), 
                (settings.EMAIL_BCC, ))
            email.send()
            return HttpResponseRedirect('/newsite_thanks')       
    else: 
        user_form       = forms.UserForm()
        ensemble_form   = forms.EnsembleForm()
    return render_to_response("web/newsite.html", {"user_form": user_form, "ensemble_form": ensemble_form})


def enter_your_name(req):    
    import base.models as M
    user       = UR.getUserInfo(req, False)
    if user is None:
        redirect_url = "/login?next=%s" % (req.META.get("PATH_INFO","/"),)
        return HttpResponseRedirect(redirect_url)
    user_form = forms.EnterYourNameUserForm(instance=user)        
    if req.method == 'POST':
        user_form = forms.EnterYourNameUserForm(req.POST, instance=user)
        if user_form.is_valid():             
            user_form.save()            
            return HttpResponseRedirect("/?ckey=%s" % (user.confkey,))         
    return render_to_response("web/enteryourname.html", {"user_form": user_form})

def add_html_doc(req, ensemble_id): 
    import base.models as M
    user       = UR.getUserInfo(req, False)
    if user is None:
        redirect_url = "/login?next=%s" % (req.META.get("PATH_INFO","/"),)
        return HttpResponseRedirect(redirect_url)
    if not auth.canEditEnsemble(user.id, ensemble_id):
        return HttpResponseRedirect("/notallowed")
    addform = forms.Html5Form()
    if req.method == 'POST':
        addform = forms.Html5Form(req.POST)
        if addform.is_valid():             
            source = M.Source()
            source.numpages = 1
            source.w = 0
            source.h = 0
            source.rotation = 0
            source.version = 0
            source.type = 4
            source.submittedby=user
            source.title = addform.cleaned_data['title']
            source.save()            
            ownership = M.Ownership()
            ownership.source = source
            ownership.ensemble_id = ensemble_id
            ownership.save()
            info = M.HTML5Info()
            info.source = source
            info.url = addform.cleaned_data['url']
            info.save();
            return HttpResponseRedirect("/")         
    return render_to_response("web/add_html_doc.html", {"form": addform})


def comment(req, id_comment): 
    #id_comment = int(id_comment)
    c = M.Comment.objects.get(pk=id_comment)    
    #id_source = annotations.getSourceForComment(id_comment)
    #[id_comment]
    org=("&org="+req.GET["org"]) if "org" in req.GET else ""
    do_reply = "&reply=1" if req.path.split("/")[1]=="r" else ""
    return HttpResponseRedirect("/f/%s?c=%s%s%s" % (c.location.source.id, id_comment, org, do_reply))
    
def invite(req): 
    pass #SACHA TODO

def logout(req): 
    o = {}
    r = render_to_response("web/logout.html", {"o": o})
    user = UR.getUserInfo(req, False)
    if user is not None and user.guest: 
        r.set_cookie("pgid", user.id, 1e9)
    r.delete_cookie("userinfo")
    r.delete_cookie("ckey")
    from django.contrib.auth import logout as djangologout
    djangologout(req)
    return r

def confirm_invite(req):        
    invite_key  = req.GET.get("invite_key", None)
    invite      = M.Invite.objects.get(key=invite_key)
    m = M.Membership.objects.filter(user=invite.user, ensemble=invite.ensemble)
    if m.count() > 0:
        m = m[0]
    else: 
        m = M.Membership(user=invite.user, ensemble=invite.ensemble)
    m.admin = invite.admin
    m.section = invite.section
    m.save()
    if invite.user.valid == False:
        invite.user.valid=True
        invite.user.save()
    r = render_to_response("web/confirm_invite.html", {"o": m})
    return r

def subscribe(req):
    key     = req.GET.get("key", "")
    e       = M.Ensemble.objects.get(invitekey=key)
    if not e.use_invitekey: 
        return HttpResponseRedirect("/notallowed")    
    auth_user       = UR.getUserInfo(req)
    user = None
    P = {"ensemble": e, "key": key}   
    if req.method == 'POST':
        if auth_user is None:
            user = M.User(confkey="".join([choice(string.ascii_letters+string.digits) for i in xrange(0,32)]))
            user_form = forms.UserForm(req.POST, instance=user)
            if user_form.is_valid(): 
                user_form.save()  
                m = M.Membership(user=user, ensemble=e)
                m.save() #membership exists but user is still invalid until has confirmed their email
                p = {"tutorial_url": settings.GUEST_TUTORIAL_URL, "conf_url": "%s://%s/?ckey=%s" %(settings.PROTOCOL, settings.NB_SERVERNAME, user.confkey), "firstname": user.firstname, "email": user.email, "password": user.password }
                email = EmailMessage(
                "Welcome to NB, %s" % (user.firstname,),
                render_to_string("email/confirm_subscribe", p), 
                settings.EMAIL_FROM, 
                (user.email, ), 
                (settings.EMAIL_BCC, ))
                email.send()
                return HttpResponseRedirect('/subscribe_thanks')
            else: 
                P["form"] = forms.UserForm(req.POST, instance=user)
                return render_to_response("web/subscribe_newuser.html", P)   
        else: 
            user = auth_user
            m = M.Membership.objects.filter(user=user, ensemble=e)
            if m.count() ==0: 
                m = M.Membership(user=user, ensemble=e)
                m.save()
            return HttpResponseRedirect('/')
        #user_form = forms.EnterYourNameUserForm(req.POST, instance=user)        
    else: 
        if auth_user is not None:
            P["user"] = auth_user
            P["form"] = forms.UserForm(instance=user)
            return render_to_response("web/subscribe_existinguser.html", P)
        else:        
            P["form"] = forms.UserForm()
            return render_to_response("web/subscribe_newuser.html", P)
                    
    


def properties_ensemble(req, id):
    user       = UR.getUserInfo(req)
    if user is None: 
        return HttpResponseRedirect("/login?next=%s" % (req.META.get("PATH_INFO","/"),))
    if not auth.canEditEnsemble(user.id, id):
        return HttpResponseRedirect("/notallowed")
    ensemble = M.Ensemble.objects.get(pk=id)
    ensemble_form = None
    if req.method=="POST": 
        ensemble_form = forms.EnsembleForm(req.POST, instance=ensemble)  
        if ensemble_form.is_valid(): 
            ensemble_form.save()   
            return HttpResponseRedirect('/admin')   
    else: 
        ensemble_form = forms.EnsembleForm(instance=ensemble)
    return render_to_response("web/properties_ensemble.html", {"form": ensemble_form, "conf_url":  "%s://%s/subscribe?key=%s" %(settings.PROTOCOL, settings.NB_SERVERNAME, ensemble.invitekey)})


def properties_ensemble_users(req, id):
    user       = UR.getUserInfo(req)
    if user is None: 
        return HttpResponseRedirect("/login?next=%s" % (req.META.get("PATH_INFO","/"),))
    if not auth.canEditEnsemble(user.id, id):
        return HttpResponseRedirect("/notallowed")
    ensemble = M.Ensemble.objects.get(pk=id)
    memberships = M.Membership.objects.filter(ensemble=ensemble)
    pendingconfirmations = memberships.filter(user__in=M.User.objects.filter(valid=False), deleted=False)
    real_memberships = memberships.filter(user__in=M.User.objects.filter(valid=True), deleted=False)    
    deleted_memberships =  memberships.filter(user__in=M.User.objects.filter(valid=True), deleted=True)
    pendinginvites = M.Invite.objects.filter(ensemble=ensemble).exclude(user__id__in=real_memberships.values("user_id"))    
    if "action" in req.GET and "membership_id" in req.GET: 
        if req.GET["action"] == "delete": 
            m = real_memberships.filter(id=req.GET["membership_id"])
            if len(m):
                m = m[0]
                m.deleted = True
                m.save()
                return HttpResponseRedirect(req.path)   
        elif req.GET["action"] == "undelete":
            m = deleted_memberships.filter(id=req.GET["membership_id"])
            if len(m):
                m = m[0]
                m.deleted = False
                m.save()
                return HttpResponseRedirect(req.path)   
        elif req.GET["action"] == "admin":
            m = real_memberships.filter(id=req.GET["membership_id"])
            if len(m):
                m = m[0]
                m.admin = True
                m.save()
                return HttpResponseRedirect(req.path)      
        elif req.GET["action"] == "unadmin":
            m = real_memberships.filter(id=req.GET["membership_id"])
            if len(m):
                m = m[0]
                m.admin = False
                m.save()
                return HttpResponseRedirect(req.path)
    return render_to_response("web/properties_ensemble_users.html", {"ensemble": ensemble, "memberships": real_memberships, "pendinginvites": pendinginvites, "pendingconfirmations": pendingconfirmations, "deleted_memberships": deleted_memberships})

def spreadsheet(req):
    return __serve_page(req, settings.SPREADSHEET_TEMPLATE, False, "/login?next=%s" % (req.get_full_path(),), mimetype="text/html")

def fbchannel(req):
    import datetime
    r = HttpResponse('<script src="//connect.facebook.net/en_US/all.js"></script>')
    r["Pragma"] = "Public"    
    cache_expire = 60*60*24*365
    r["Cache-Control"] = "max-age="+cache_expire
    r["Expires"]=(datetime.datetime.now()+datetime.timedelta(cache_expire)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    return r


 
#   
# UR.getUserInfo(req)
#    if user is None: 
#        return HttpResponseRedirect("/login?next=%s" % (req.get_full_path(),))
#    if "id_ensemble" not in req.GET: 
#        from django.http import HttpResponse
#        return HttpResponse("missing id_ensemble")
#    id_ensemble = req.GET["id_ensemble"]
#    if not auth.canEditEnsemble(user.id,id_ensemble):
#        return HttpResponseRedirect("/notallowed")
#       

def openid_index(request):
    s = ['<p>']
    if request.user.is_authenticated():
        s.append('You are signed in as <strong>%s</strong> (%s)' % (
                escape(request.user.username),
                escape(request.user.get_full_name())))
        s.append(' | <a href="/openid_logout">Sign out</a>')
    else:
        s.append('<a href="/openid/login">Sign in with OpenID</a>')
    s.append('</p>')
    s.append('<p><a href="/private">This requires authentication</a></p>')
    return HttpResponse('\n'.join(s))


def facebooksample(request):
    #without that we we get an error when visiting /openid/login/ (ViewDoesNotExist at /openid/login/)
    #cf: http://stackoverflow.com/questions/6324799/django-templatesyntaxerror
    return HttpResponse('Nothing here.')
def debug(request):
    #without that we we get an error when visiting /openid/login/ (ViewDoesNotExist at /openid/login/)
    #cf: http://stackoverflow.com/questions/6324799/django-templatesyntaxerror
    return HttpResponse('Nothing here.')


@login_required
def require_authentication(request):
    return HttpResponse('This page requires authentication')



@receiver(post_save, sender=User)
def user_post_save_handler(sender, **kwargs): 
    user = kwargs["instance"]
    u = None
    if user is not None: 
        email = user.email
        try: 
            u = M.User.objects.get(email=email)
            if u.firstname == "" or u.lastname== "":
                u.firstname = user.first_name
                u.lastname = user.last_name
                u.save()
        except M.User.DoesNotExist: 
            password = "".join([ random.choice(string.ascii_letters+string.digits) for i in xrange(0,6)])
            confkey =  "".join([ random.choice(string.ascii_letters+string.digits) for i in xrange(0,32)])
            u = M.User(email=email, firstname=user.first_name, lastname=user.last_name, password=password, confkey=confkey, guest=False, valid=True )
            u.save()
