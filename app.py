from flask import Flask, request, redirect, render_template_string, g, url_for
import sqlite3, random, os, csv

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "problems.db")

ADMIN_TMPL = """
<!doctype html>
<html>
<head>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100 min-h-screen">
<div class="max-w-3xl mx-auto py-10">
  <h1 class="text-2xl font-bold mb-4">관리자 모드</h1>
  <form class="space-y-3" method="post">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 bg-white p-4 rounded shadow" autocomplete="off">
      <select name="stage" required class="border p-2 rounded w-full">
        <option value="">단계 선택 (1~6)</option>
        {% for s in range(1,7) %}
        <option value="{{s}}">단계 {{s}}</option>
        {% endfor %}
      </select>
      <input name="question" required placeholder="문제" class="border p-2 rounded w-full" autocomplete="off">
      <input name="answer" required placeholder="정답" class="border p-2 rounded w-full" autocomplete="off">
      <button class="md:col-span-3 bg-blue-600 text-white py-2 rounded hover:bg-blue-700">저장하기</button>
    </div>
  </form>

  <div class="mb-4 flex gap-2">
    <form method="post" action="{{ url_for('admin_load_sample') }}" style="display: inline;" onsubmit="return confirm('샘플 데이터를 불러오시겠습니까? 기존 데이터는 유지됩니다.');">
      <button type="submit" class="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700">샘플 불러오기</button>
    </form>
  </div>

  <h2 class="text-xl font-semibold mt-8 mb-3">저장된 문제</h2>
  {% if rows %}
  <div class="mb-3 flex gap-2">
    <button onclick="saveAll()" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">모두 저장</button>
    <form method="post" action="{{ url_for('admin_delete_all') }}" style="display: inline;" onsubmit="return confirm('모든 문제를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.');">
      <button type="submit" class="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">모두 삭제</button>
    </form>
  </div>
  {% endif %}
  <div class="bg-white rounded shadow divide-y">
    {% for row in rows %}
      <form class="problem-form p-3 flex flex-col gap-2 md:flex-row md:items-center md:gap-3" method="post" action="{{ url_for('admin_update', pid=row['id']) }}">
        <input type="hidden" name="_method" value="update">
        <input type="hidden" name="problem_id" value="{{row['id']}}">
        <input name="stage" type="number" min="1" max="6" required value="{{row['stage']}}" class="border p-2 rounded w-full md:w-24" />
        <input name="question" required value="{{row['question']}}" class="border p-2 rounded w-full md:flex-1" />
        <input name="answer" required value="{{row['answer']}}" class="border p-2 rounded w-full md:w-48" />
        <div class="flex gap-2">
          <button type="button" onclick="this.closest('form').submit()" class="bg-green-600 text-white px-3 py-2 rounded hover:bg-green-700">저장</button>
          <button formaction="{{ url_for('admin_delete', pid=row['id']) }}" formmethod="post" class="bg-red-600 text-white px-3 py-2 rounded hover:bg-red-700" onclick="return confirm('삭제하시겠습니까?');">삭제</button>
        </div>
      </form>
    {% endfor %}
    {% if not rows %}
      <div class="p-3 text-gray-500">아직 문제 없음</div>
    {% endif %}
  </div>
  <script>
    function saveAll() {
      const forms = document.querySelectorAll('.problem-form');
      const updates = [];
      
      forms.forEach(form => {
        const formData = new FormData(form);
        const pid = formData.get('problem_id');
        const stage = formData.get('stage');
        const question = formData.get('question');
        const answer = formData.get('answer');
        
        if (pid && stage && question && answer) {
          updates.push({
            id: pid,
            stage: stage,
            question: question,
            answer: answer
          });
        }
      });
      
      if (updates.length === 0) {
        alert('저장할 문제가 없습니다.');
        return;
      }
      
      // 모든 업데이트를 한 번에 전송
      fetch('{{ url_for("admin_update_all") }}', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ updates: updates })
      })
      .then(response => {
        if (response.ok) {
          window.location.reload();
        } else {
          alert('저장 중 오류가 발생했습니다.');
        }
      })
      .catch(error => {
        alert('저장 중 오류가 발생했습니다: ' + error);
      });
    }
  </script>

  <div class="mt-6">
    <a href="{{ url_for('quiz_select') }}" class="text-blue-700 underline">문제 출제 모드로 가기</a>
  </div>
</div>
</body>
</html>
"""

SELECT_TMPL = """
<!doctype html>
<html>
<head><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen">
<div class="max-w-xl mx-auto py-10">
  <h1 class="text-2xl font-bold mb-4">문제 출제 모드</h1>
  <form method="post" class="bg-white p-4 rounded shadow space-y-3">
    <label class="block text-sm text-gray-600">단계를 선택하세요</label>
    <select name="stage" class="border p-2 rounded w-full" required>
      <option value="">-- 단계 선택 --</option>
      {% for s in stages %}
        <option value="{{s}}">단계 {{s}}</option>
      {% endfor %}
    </select>
    <button class="bg-blue-600 text-white py-2 rounded w-full hover:bg-blue-700">시작</button>
  </form>
  <div class="mt-4">
    <a href="{{ url_for('admin') }}" class="text-blue-700 underline text-sm">관리자 모드</a>
  </div>
</div>
</body>
</html>
"""

QUIZ_TMPL = """
<!doctype html>
<html>
<head><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen">
<div class="max-w-xl mx-auto py-10">
  <h1 class="text-2xl font-bold mb-4">단계 {{stage}} 문제</h1>
  {% if not question %}
    <div class="bg-white p-4 rounded shadow">해당 단계에 문제가 없습니다.</div>
  {% else %}
    <form method="post" class="bg-white p-4 rounded shadow space-y-3" autocomplete="off">
      <div class="text-lg font-semibold">{{question['question']}}</div>
      <input type="hidden" name="qid" value="{{question['id']}}">
      <input name="user_answer" required placeholder="정답 입력" class="border p-2 rounded w-full" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" value="">
      <button class="bg-green-600 text-white py-2 rounded w-full hover:bg-green-700">제출</button>
      {% if result is not none %}
        <div class="p-3 rounded {{ 'bg-green-100 text-green-800' if result else 'bg-red-100 text-red-800' }}">
          {{ 'O 정답! 다음 단계로 진행하세요.' if result else 'X 오답! 다시 시도해보세요.' }}
        </div>
        {% if result %}
          <div class="text-sm text-gray-700">현재 단계 완료! 다음 단계로 진행하세요.</div>
        {% else %}
          <div id="correct-ans" class="p-3 mt-2 rounded bg-yellow-100 text-yellow-900">
            정답: {{ correct_answer }}
          </div>
          <div class="text-sm text-gray-700 mt-1">2초 후 정답 노출이 사라집니다. 다시 시도해보세요.</div>
          <script>
            setTimeout(() => {
              const el = document.getElementById("correct-ans");
              if (el) el.classList.add("hidden");
            }, 2000);
          </script>
        {% endif %}
        <script>
          // 2초 후 동일 단계의 새로운 랜덤 문제로 이동
          setTimeout(() => {
            window.location.href = "{{ url_for('quiz', stage=stage) }}";
          }, 2000);
        </script>
      {% endif %}
    </form>
  {% endif %}
</div>
</body>
</html>
"""

def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exc):
    if "db" in g:
        g.db.close()

def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS problems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stage INTEGER NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL
    )
    """)
    conn.commit()

@app.route("/admin", methods=["GET", "POST"])
def admin():
    init_db()
    db = get_db()
    if request.method == "POST":
        stage = int(request.form["stage"])
        question = request.form["question"].strip()
        answer = request.form["answer"].strip()
        if question and answer:
            db.execute("INSERT INTO problems(stage, question, answer) VALUES (?,?,?)",
                       (stage, question, answer))
            db.commit()
        return redirect(url_for("admin"))
    rows = db.execute("SELECT * FROM problems ORDER BY stage, id DESC").fetchall()
    return render_template_string(ADMIN_TMPL, rows=rows)

@app.route("/admin/update/<int:pid>", methods=["POST"])
def admin_update(pid):
    init_db()
    db = get_db()
    stage = request.form.get("stage")
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()
    if stage and question and answer:
        db.execute(
            "UPDATE problems SET stage=?, question=?, answer=? WHERE id=?",
            (int(stage), question, answer, pid),
        )
        db.commit()
    return redirect(url_for("admin"))

@app.route("/admin/update-all", methods=["POST"])
def admin_update_all():
    init_db()
    db = get_db()
    data = request.get_json()
    if data and "updates" in data:
        for update in data["updates"]:
            pid = update.get("id")
            stage = update.get("stage")
            question = update.get("question", "").strip()
            answer = update.get("answer", "").strip()
            if pid and stage and question and answer:
                try:
                    db.execute(
                        "UPDATE problems SET stage=?, question=?, answer=? WHERE id=?",
                        (int(stage), question, answer, int(pid)),
                    )
                except Exception as e:
                    pass  # 개별 업데이트 실패 시 계속 진행
        db.commit()
    return {"status": "success"}, 200

@app.route("/admin/delete/<int:pid>", methods=["POST"])
def admin_delete(pid):
    init_db()
    db = get_db()
    db.execute("DELETE FROM problems WHERE id=?", (pid,))
    db.commit()
    return redirect(url_for("admin"))

@app.route("/admin/delete-all", methods=["POST"])
def admin_delete_all():
    init_db()
    db = get_db()
    db.execute("DELETE FROM problems")
    db.commit()
    return redirect(url_for("admin"))

@app.route("/admin/load-sample", methods=["POST"])
def admin_load_sample():
    init_db()
    db = get_db()
    sample_path = os.path.join(os.path.dirname(__file__), "sample.csv")
    
    try:
        with open(sample_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                stage = row.get('단계', '').strip()
                question = row.get('문제', '').strip()
                answer = row.get('정답', '').strip()
                
                if stage and question and answer:
                    try:
                        stage_num = int(stage)
                        if 1 <= stage_num <= 6:
                            db.execute(
                                "INSERT INTO problems(stage, question, answer) VALUES (?,?,?)",
                                (stage_num, question, answer)
                            )
                            count += 1
                    except ValueError:
                        continue
            db.commit()
    except FileNotFoundError:
        pass
    except Exception as e:
        pass
    
    return redirect(url_for("admin"))

@app.route("/", methods=["GET", "POST"])
def quiz_select():
    init_db()
    db = get_db()
    stages = [r["stage"] for r in db.execute("SELECT DISTINCT stage FROM problems ORDER BY stage")]
    if request.method == "POST":
        stage = request.form["stage"]
        return redirect(url_for("quiz", stage=stage))
    return render_template_string(SELECT_TMPL, stages=stages)

@app.route("/quiz/<stage>", methods=["GET", "POST"])
def quiz(stage):
    init_db()
    db = get_db()
    question = None
    result = None
    next_stage = None
    correct_answer = None

    if request.method == "POST":
        qid = request.form.get("qid")
        if qid:
            # 제출된 문제를 다시 불러와 동일 문제로 채점
            question = db.execute(
                "SELECT * FROM problems WHERE id=? AND stage=?", (qid, stage)
            ).fetchone()
            if not question:
                # 혹시 단계가 바뀐 경우를 대비해 id만으로도 검색
                question = db.execute(
                    "SELECT * FROM problems WHERE id=?", (qid,)
                ).fetchone()
            if question:
                user_answer = request.form["user_answer"].strip()
                result = (user_answer == question["answer"])
                if result:
                    try:
                        next_stage = min(6, int(stage) + 1)
                    except ValueError:
                        next_stage = None
                else:
                    correct_answer = question["answer"]
    else:
        rows = db.execute("SELECT * FROM problems WHERE stage=?", (stage,)).fetchall()
        question = random.choice(rows) if rows else None

    return render_template_string(
        QUIZ_TMPL,
        stage=stage,
        question=question,
        result=result,
        next_stage=next_stage,
        correct_answer=correct_answer,
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)