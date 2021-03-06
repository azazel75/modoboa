from django.db import transaction, IntegrityError
from django.utils.translation import ugettext as _, ungettext
from django.shortcuts import render
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import (
    login_required, permission_required
)
from modoboa.lib import events
from modoboa.lib.webutils import render_to_json_response
from modoboa.lib.exceptions import PermDeniedException, Conflict
from modoboa.extensions.admin.forms import AliasForm
from modoboa.extensions.admin.models import Alias


def _validate_alias(request, form, successmsg, callback=None):
    """Alias validation

    Common function shared between creation and modification actions.
    """
    if form.is_valid():
        form.set_recipients()
        try:
            alias = form.save()
        except IntegrityError:
            raise Conflict(_("Alias with this name already exists"))
        if callback:
            callback(request.user, alias)
        return render_to_json_response(successmsg)

    return render_to_json_response({'form_errors': form.errors}, status=400)


def _new_alias(request, title, action, successmsg,
               tplname="admin/aliasform.html"):
    events.raiseEvent("CanCreate", request.user, "mailbox_aliases")
    if request.method == "POST":
        def callback(user, alias):
            alias.post_create(user)

        form = AliasForm(request.user, request.POST)
        return _validate_alias(
            request, form, successmsg, callback
        )

    ctx = {
        "title": title,
        "action": action,
        "formid": "aliasform",
        "action_label": _("Create"),
        "action_classes": "submit",
        "form": AliasForm(request.user)
    }
    return render(request, tplname, ctx)


@login_required
@permission_required("admin.add_alias")
@transaction.commit_on_success
def newdlist(request):
    return _new_alias(
        request, _("New distribution list"), reverse(newdlist),
        _("Distribution list created")
    )


@login_required
@permission_required("admin.add_alias")
@transaction.commit_on_success
def newalias(request):
    return _new_alias(
        request, _("New alias"), reverse(newalias),
        _("Alias created")
    )


@login_required
@permission_required("admin.add_alias")
@transaction.commit_on_success
def newforward(request):
    return _new_alias(
        request, _("New forward"), reverse(newforward),
        _("Forward created")
    )


@login_required
@permission_required("admin.change_alias")
@transaction.commit_on_success
def editalias(request, alid, tplname="admin/aliasform.html"):
    alias = Alias.objects.get(pk=alid)
    if not request.user.can_access(alias):
        raise PermDeniedException
    if request.method == "POST":
        if len(alias.get_recipients()) >= 2:
            successmsg = _("Distribution list modified")
        elif alias.extmboxes != "":
            successmsg = _("Forward modified")
        else:
            successmsg = _("Alias modified")
        form = AliasForm(request.user, request.POST, instance=alias)
        return _validate_alias(request, form, successmsg)

    ctx = {
        'action': reverse(editalias, args=[alias.id]),
        'formid': 'aliasform',
        'title': alias.full_address,
        'action_label': _('Update'),
        'action_classes': 'submit',
        'form': AliasForm(request.user, instance=alias)
    }
    return render(request, tplname, ctx)


@login_required
@permission_required("admin.delete_alias")
@transaction.commit_on_success
def delalias(request):
    selection = request.GET["selection"].split(",")
    for alid in selection:
        alias = Alias.objects.get(pk=alid)
        if not request.user.can_access(alias):
            raise PermDeniedException
        if alias.type == 'dlist':
            msg = "Distribution list deleted"
            msgs = "Distribution lists deleted"
        elif alias.type == 'forward':
            msg = "Forward deleted"
            msgs = "Forwards deleted"
        else:
            msg = "Alias deleted"
            msgs = "Aliases deleted"
        alias.delete()

    msg = ungettext(msg, msgs, len(selection))
    return render_to_json_response(msg)
