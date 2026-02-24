from flask import Flask, render_template_string, request, jsonify
import subprocess
import tempfile
import os
import sys

app = Flask(__name__)

@app.route('/')
def index():
    file_name = request.args.get('file', 'pages/index.html')
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        with open('pages/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
    return render_template_string(content)


def waf(code):
    blacklisted_keywords = [
        'import', 'open', 'read', 'write', 'exec',
        'eval', '__', 'os', 'sys', 'subprocess',
        'run', 'flag', '\'', '\"'
    ]
    for keyword in blacklisted_keywords:
        if keyword in code:
            return False
    return True


@app.route('/execute', methods=['POST'])
def execute_code():
    code = request.json.get('code', '')
    if not code:
        return jsonify({'error': '请输入Python代码'})

    if not waf(code):
        return jsonify({'error': 'Hacker!'})

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(f"""import sys

sys.modules['os'] = 'not allowed'

def is_my_love_event(event_name):
    return event_name.startswith("Nothing is my love but you.")

def my_audit_hook(event_name, arg):
    if len(event_name) > 0:
        raise RuntimeError("Too long event name!")
    if len(arg) > 0:
        raise RuntimeError("Too long arg!")
    if not is_my_love_event(event_name):
        raise RuntimeError("Hacker out!")

__import__('sys').addaudithook(my_audit_hook)

{code}
""")
            temp_file_name = f.name

        result = subprocess.run(
            [sys.executable, temp_file_name],
            capture_output=True,
            text=True,
            timeout=10
        )

        os.unlink(temp_file_name)

        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': '代码执行超时（超过10秒）'})
    except Exception as e:
        return jsonify({'error': f'执行出错: {str(e)}'})
    finally:
        if 'temp_file_name' in locals() and os.path.exists(temp_file_name):
            os.unlink(temp_file_name)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)