import random
import crypt
import os
import repository
import settings
from app.modhg.HGWeb import HGWeb

LOGIN_PASSWD_SEP = ":"

def list(filename):
    lines = _get_rows(filename)
    login_list = []
    for line in lines:
        login, hash = line.split(':')
        login_list.append(login)
    login_list.sort()
    return login_list

def exists(filename,login):
    lines = _get_rows(filename)
    match = [line for line in lines if line.split(LOGIN_PASSWD_SEP)[0] == login]
    if match:
        return True
    return False


def add(filename,login,password):
    lines = _get_rows(filename)
    match = [line for line in lines if line.split(LOGIN_PASSWD_SEP)[0] == login]
    if match:
        raise ValueError("User exists")
    row = _form_file_row(login, password)
    lines.append(row)
    open(filename,'w+').writelines(lines)

def remove(filename, login):
    # todo: check is user exists in hgrc files
    _remove_from_hgrc(login)
    lines = open(filename, 'r').readlines()
    matches = [line for line in lines if not line.split(LOGIN_PASSWD_SEP)[0] == login]
    open(filename,'w+').writelines(matches)

def update(filename, login, new_password):
    lines = _get_rows(filename)
    match = [line for line in lines if line.startswith(login)]
    if not match:
        raise ValueError("User not found")
    matches = [line for line in lines if not line.startswith(login)]
    row = _form_file_row(login, new_password)
    matches.append(row)
    open(filename,'w+').writelines(matches)

def permissions(login, path_as_key = False):
    #check is login exists
    permission_list = {}
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    global_web = hgweb.get_web()
    paths = hgweb.get_paths()
    for (name, path) in paths:
        if path.endswith("*"):
            permission_list.update(_scan(name, path, path.endswith("**"), login, path_as_key, global_web))
        else:
            if repository.is_repository(path):
                perm = _extract_permission(login, path, global_web)
                if perm:
                    key = path if path_as_key else name.strip(os.sep)
                    permission_list[key] = perm
    return  permission_list

def _scan(name, dir, deep, login, path_as_key, global_web):
    permission_list = {}
    dir = dir.rstrip("*")
    if not os.path.exists(dir):
        return permission_list
    dir_list = os.listdir(dir)
    for current_dir in dir_list:
        path = os.path.join(dir, current_dir)
        if repository.is_repository(path):
            perm = _extract_permission(login, path, global_web)
            if perm:
                key = path if path_as_key else os.path.join(name, current_dir)
                permission_list[key] = perm
        elif deep:
            permission_list.update(_scan(os.path.join(name, current_dir), path, deep, login, path_as_key, global_web))
    return permission_list

def _extract_permission(login, path, global_web):
    hgrc_path = os.path.join(path,".hg","hgrc")
    if not os.path.exists(hgrc_path):
        return False
    hgrc = HGWeb(hgrc_path)
    web = hgrc.get_web()
    allow_read = not _is_in_list(web, global_web, "deny_read", login) and \
                 _is_in_list(web, global_web, "allow_read", login)
    allow_push = not _is_in_list(web, global_web, "deny_push", login) and \
                 _is_in_list(web, global_web, "allow_push", login)
    if allow_read or allow_push:
        return {"read": allow_read, "push": allow_push}
    return False


def _is_in_list_single(web, key, login, is_global=False):
    if web is None:
        if is_global and key=="allow_read":
            return True
        raise ValueError()
    res = [value for (name, value) in web if name==key]
    if not len(res):
        if is_global and key=="allow_read":
            return True
        raise ValueError()
    value = res[0].strip()
    if value.find("*")>=0:
        return True
    if value=="" and key=="allow_read":
        return True
    raw_login_list = value.split(",")
    login_list = [ item.strip() for item in raw_login_list]
    try:
        login_list.index(login)
        return True
    except ValueError:
        return False

def _is_in_list(web, global_web, key, login):
    try:
        return _is_in_list_single(web, key, login)
    except ValueError:
        try:
            return _is_in_list_single(global_web, key, login, True)
        except ValueError:
            return False

def _remove_from_hgrc(login):
    _remove_hgrc_single(login, settings.HGWEB_CONFIG)
    hgweb = HGWeb(settings.HGWEB_CONFIG)
    paths = hgweb.get_paths()
    for (name, path) in paths:
        if path.endswith("*"):
            _remove_from_hgrc_int(name, path, path.endswith("**"), login)
        else:
            _remove_hgrc_single(login, path)

def _remove_from_hgrc_int(name, dir, deep, login):
    dir = dir.rstrip("*")
    if not os.path.exists(dir):
        return
    dir_list = os.listdir(dir)
    for current_dir in dir_list:
        path = os.path.join(dir, current_dir)
        if repository.is_repository(path):
            _remove_hgrc_single(login, path)
        elif deep:
            _remove_from_hgrc_int(os.path.join(name, current_dir), path, deep, login)

def _remove_hgrc_single(login, path):
    if os.path.isfile(path):
        hgrc = HGWeb(path)
    else:
        if not repository.is_repository(path):
            return
        hgrc_path = os.path.join(path,".hg","hgrc")
        if not os.path.exists(hgrc_path):
            return
        hgrc = HGWeb(hgrc_path)
    required_keys = ["allow_read", "allow_push", "deny_read", "deny_push"]
    for key in required_keys:
        val = hgrc.get_web_key(key)
        if not val is None:
            raw_login_list = val.split(",")
            login_list = [item.strip() for item in raw_login_list]
            try:
                login_list.remove(login)
                logins = ",".join(login_list)
                hgrc.set_web_key(key, logins)
            except ValueError:
                continue

def _salt():
    letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.'
    return random.choice(letters) + random.choice(letters)

def _form_file_row(login, password):
    return login + ":" + crypt.crypt(password, _salt()) + os.linesep

def _get_rows(filename):
    lines = open(filename, 'r').readlines()
    return [line.strip("\r\n") + os.linesep for line in lines]
