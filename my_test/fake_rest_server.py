from flask import Flask, jsonify, request
import json
import time

app = Flask(__name__)

tasks = [
    {
        'id': 1,
        'title': 'aaaaa',
        'done': False
    }
]
token = "123"


def get_max_id(extend_items=None):
    t_id = -1
    for i in tasks:
        if t_id < i['id']:
            t_id = i['id']
    if extend_items:
        for i in extend_items:
            if t_id < i['id']:
                t_id = i['id']
    return t_id


@app.route('/token', methods=['POST'])
def post_token():
    global token
    token = str(time.time())
    res = {"status": "Created",
           "Token": token}
    print(res)
    return json.dumps(res), 201


@app.route('/clear_all', methods=['POST'])
def clear_all():
    global token
    token = str(time.time())
    tasks.clear()
    res = {"status": "Cleared"}
    print(res)
    return json.dumps(res), 204


@app.route('/get_form_response', methods=['GET'])
def get_form_response():
    return "param1=1&param2=2", 200


@app.route('/tasks_form', methods=['POST'])
def tasks_form_operations():
    print("Parameters: ", request.args)
    print("Headers: ", request.headers)
    global tasks, token

    token_t = request.headers.get('Token', None)
    # if token_t != token:
    if token_t == None:
        res = {"status": "ERROR",
               "msg": "Permission Denied, No Token specified",
               "info": request.args}
        return jsonify(res), 401

    if request.method == "POST":
        body_s = request.get_data()
        if isinstance(body_s, bytes):
            body_s = body_s.decode()
        form = request.form
        print("form: ", type(form), form)
        task_id = form.get("id", None)
        if task_id == None or task_id == "":
            task_id = get_max_id() + 1
        tmp = None
        task_id = int(task_id)
        for t in tasks:
            if t["id"] == task_id:
                tmp = t
                break
        if tmp != None:
            res = {"status": "ERROR",
                   "msg": "ID %s existed" % task_id,
                   "info": body_s}
            return jsonify(res), 400
        title = form.get("title")
        done = form.get("done")
        done = True if done == 'True' else False
        new_task = {"id": task_id, "title": title, "done": done}
        tasks.append(new_task)
        res = {"status": "Created",
               "info": new_task}
        return jsonify(res), 201


@app.route('/tasks', methods=['GET', 'POST'])
def tasks_operations():
    print("Parameters: ", request.args)
    print("Headers: ", request.headers)
    global tasks, token

    token_t = request.headers.get('Token', None)
    # if token_t != token:
    if token_t == None:
        res = {"status": "ERROR",
               "msg": "Permission Denied, No Token specified",
               "info": request.args}
        return jsonify(res), 401

    if request.method == "GET":
        return jsonify({'info': tasks})

    elif request.method == "POST":
        body_s = request.get_data()
        if isinstance(body_s, bytes):
            body_s = body_s.decode()
        print("body: ", body_s)
        try:
            body = json.loads(body_s)
        except:
            res = {"status": "ERROR",
                   "msg": "body is not json type: %s" % body_s,
                   "info": body_s}
            return jsonify(res), 400
        if type(body) != list:
            body = [body]
        items_added = list()
        for body_item in body:
            task_id = body_item.get("id", None)
            if task_id == None or task_id == "":
                task_id = get_max_id(items_added) + 1
            tmp = None
            task_id = int(task_id)
            for t in tasks:
                if t["id"] == task_id:
                    tmp = t
                    break
            if tmp != None:
                res = {"status": "ERROR",
                       "msg": "ID %s existed" % task_id,
                       "info": body_item}
                return jsonify(res), 400
            title = body_item.get("title")
            done = body_item.get("done")
            new_task = {"id": task_id, "title": title, "done": done}
            items_added.append(new_task)
        tasks.extend(items_added)
        res = {"status": "Created",
               "info": items_added}
        return jsonify(res), 201


@app.route('/task/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
def task_operations(task_id):
    print("Parameters: ", request.args)
    print("Headers: ", request.headers)
    global tasks, token

    token_t = request.headers.get('Token', None)
    # if token_t != token:
    if token_t == None:
        res = {"status": "ERROR",
               "msg": "Permission Denied, No Token specified",
               "info": request.args}
        return jsonify(res), 401

    if request.method == "GET":
        task = [t for t in tasks if t['id'] == task_id]
        if len(task) == 0:
            res = {"status": "ERROR",
                   "msg": "ID %s not exist" % task_id,
                   "info": request.url}
            return jsonify(res), 404
        return jsonify({'info': task})

    elif request.method == "POST":
        body_s = request.get_data()
        print("body: ", body_s)
        try:
            body = json.loads(body_s)
        except:
            res = {"status": "ERROR",
                   "msg": "body is not json type: %s" % body_s,
                   "info": body_s}
            return jsonify(res), 400
        tmp = None
        for t in tasks:
            if t["id"] == task_id:
                tmp = t
                break
        if tmp != None:
            res = {"status": "ERROR",
                   "msg": "ID %s existed" % task_id,
                   "info": body_s}
            return jsonify(res), 400
        title = body.get("title", None)
        done = body.get("done", None)
        new_task = {"id": task_id, "title": title, "done": done}
        tasks.append(new_task)
        res = {"status": "Created",
               "info": new_task}
        return jsonify(res), 201

    elif request.method == "PUT":
        body_s = request.get_data()
        if isinstance(body_s, bytes):
            body_s = body_s.decode()
        print("body: ", body_s)
        try:
            body = json.loads(body_s)
        except:
            res = {"status": "ERROR",
                   "msg": "body is not json type",
                   "info": body_s}
            return jsonify(res), 400
        task = None
        for t in tasks:
            if t["id"] == task_id:
                task = t
                break
        if task == None:
            res = {"status": "ERROR",
                   "msg": "ID %s not exist" % task_id,
                   "info": body_s}
            return jsonify(res), 404
        for key, value in list(body.items()):
            if key != "id":
                task[key] = value
        res = {"status": "Updated",
               "info": task}
        return jsonify(res), 201

    elif request.method == "DELETE":
        task_index = None
        for i, t in enumerate(tasks):
            if t["id"] == task_id:
                task_index = i
                break
        if task_index == None:
            res = {"status": "ERROR",
                   "msg": "ID %s not exist" % task_id,
                   "info": request.args}
            return jsonify(res), 400
        ret = tasks[task_index].copy()
        del tasks[task_index]
        res = {"status": "Deleted",
               "info": ret}
        return jsonify(res), 200


@app.route('/echo_request_body', methods=['POST'])
def echo_request_body():
    body = request.get_data()
    if isinstance(body, bytes):
        body = body.decode()
    return body, 200


if __name__ == '__main__':
    # app.run(debug=True, port=5000, host='0.0.0.0', ssl_context='adhoc')
    app.run(debug=True, port=5000, host='0.0.0.0')