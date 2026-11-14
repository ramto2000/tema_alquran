"""
Ekstensi Admin untuk tema_alquran_app.
Dipanggil dari app.py dengan:
    import admin_extension
    admin_extension.register_admin(app, globals())
"""
import os
import re
import json
import hmac
import sqlite3
import secrets
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from flask import (
    render_template, request, redirect, url_for, session,
    flash, abort
)

def register_admin(app, app_globals):
    base_dir = Path(app.root_path)
    db_path = base_dir / "tema_admin.sqlite3"

    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ganti-kunci-rahasia-aplikasi-ini")
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin12345")

    @contextmanager
    def db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db():
        with db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS themes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS subthemes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    theme_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    keywords TEXT NOT NULL DEFAULT '[]',
                    FOREIGN KEY(theme_id) REFERENCES themes(id) ON DELETE CASCADE,
                    UNIQUE(theme_id, name)
                );
                CREATE TABLE IF NOT EXISTS mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nomor_surat INTEGER NOT NULL,
                    nomor_ayat INTEGER NOT NULL,
                    subtheme_id INTEGER NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manual',
                    FOREIGN KEY(subtheme_id) REFERENCES subthemes(id) ON DELETE CASCADE,
                    UNIQUE(nomor_surat, nomor_ayat, subtheme_id)
                );
                CREATE TABLE IF NOT EXISTS excluded_auto (
                    nomor_surat INTEGER NOT NULL,
                    nomor_ayat INTEGER NOT NULL,
                    subtheme_id INTEGER NOT NULL,
                    PRIMARY KEY(nomor_surat, nomor_ayat, subtheme_id)
                );
            """)
            count = conn.execute("SELECT COUNT(*) FROM themes").fetchone()[0]
            if count == 0:
                for tid, name, desc, subs in app_globals["THEMES"]:
                    conn.execute(
                        "INSERT INTO themes(id,name,description) VALUES(?,?,?)",
                        (tid, name, desc)
                    )
                    for subname, keywords in subs:
                        conn.execute(
                            "INSERT INTO subthemes(theme_id,name,keywords) VALUES(?,?,?)",
                            (tid, subname, json.dumps(keywords, ensure_ascii=False))
                        )

    def refresh_catalog():
        """Bangun ulang katalog publik dan pemetaan otomatis dari database Admin."""
        with db() as conn:
            themes_rows = conn.execute(
                "SELECT id,name,description FROM themes ORDER BY id"
            ).fetchall()
            sub_rows = conn.execute(
                "SELECT id,theme_id,name,keywords FROM subthemes ORDER BY id"
            ).fetchall()

            by_theme = {}
            sub_by_id = {}
            for row in sub_rows:
                try:
                    keywords = json.loads(row["keywords"] or "[]")
                except (TypeError, ValueError):
                    keywords = []
                keywords = [str(k).strip().lower() for k in keywords if str(k).strip()]
                by_theme.setdefault(row["theme_id"], []).append((row["name"], keywords))
                sub_by_id[row["id"]] = {
                    "id": row["id"], "theme_id": row["theme_id"],
                    "name": row["name"], "keywords": keywords
                }

            catalog = [
                (t["id"], t["name"], t["description"], by_theme.get(t["id"], []))
                for t in themes_rows
            ]
            app_globals["THEMES"] = catalog

            # Refresh hanya pemetaan otomatis. Pemetaan manual tetap disimpan.
            conn.execute("DELETE FROM mappings WHERE source='auto'")
            ayat_df = app_globals["AYAT"]
            for verse in ayat_df.to_dict("records"):
                try:
                    surah = int(verse["nomor_surat"])
                    ayah = int(verse["nomor_ayat"])
                except (TypeError, ValueError, KeyError):
                    continue
                translation = str(verse.get("terjemahan_indonesia", "")).lower()
                for sub in sub_rows:
                    try:
                        keys = json.loads(sub["keywords"] or "[]")
                    except (TypeError, ValueError):
                        keys = []
                    if any(str(k).strip().lower() in translation for k in keys if str(k).strip()):
                        excluded = conn.execute(
                            """SELECT 1 FROM excluded_auto
                               WHERE nomor_surat=? AND nomor_ayat=? AND subtheme_id=?""",
                            (surah, ayah, sub["id"])
                        ).fetchone()
                        if not excluded:
                            conn.execute(
                                """INSERT OR IGNORE INTO mappings
                                   (nomor_surat,nomor_ayat,subtheme_id,source)
                                   VALUES(?,?,?,'auto')""",
                                (surah, ayah, sub["id"])
                            )

            mapping_rows = conn.execute("""
                SELECT m.id AS mapping_id, m.nomor_surat, m.nomor_ayat,
                       m.source, s.id AS subtheme_id, s.name AS subtema,
                       t.id AS id_tema, t.name AS tema
                FROM mappings m
                JOIN subthemes s ON s.id=m.subtheme_id
                JOIN themes t ON t.id=s.theme_id
                ORDER BY m.nomor_surat,m.nomor_ayat,t.id,s.id
            """).fetchall()

        ayat_lookup = {}
        for verse in app_globals["AYAT"].to_dict("records"):
            try:
                key = (int(verse["nomor_surat"]), int(verse["nomor_ayat"]))
            except (TypeError, ValueError, KeyError):
                continue
            ayat_lookup[key] = verse

        result = []
        for m in mapping_rows:
            key = (m["nomor_surat"], m["nomor_ayat"])
            verse = ayat_lookup.get(key, {})
            result.append({
                "mapping_id": m["mapping_id"],
                "nomor_global": verse.get("nomor_global", ""),
                "nomor_surat": m["nomor_surat"],
                "nama_surat": app_globals["NAMA_SURAT"].get(m["nomor_surat"], ""),
                "nomor_ayat": m["nomor_ayat"],
                "teks_arab": verse.get("teks_arab", ""),
                "terjemahan_indonesia": verse.get("terjemahan_indonesia", ""),
                "id_tema": m["id_tema"], "tema": m["tema"],
                "subtema": m["subtema"], "source": m["source"]
            })
        app_globals["MAPPING"] = result

    def csrf_token():
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    @app.context_processor
    def inject_csrf():
        return {"csrf_token": csrf_token}

    @app.template_filter("fromjson")
    def fromjson_filter(value):
        try:
            result = json.loads(value or "[]")
            return result if isinstance(result, list) else []
        except (TypeError, ValueError):
            return []

    @app.before_request
    def protect_admin_posts():
        if request.method == "POST" and request.path.startswith("/admin"):
            supplied = request.form.get("_csrf", "")
            expected = session.get("_csrf_token", "")
            if not expected or not hmac.compare_digest(supplied, expected):
                abort(400, description="Token keamanan tidak valid. Muat ulang halaman lalu coba lagi.")

    def admin_required(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not session.get("admin_logged_in"):
                return redirect(url_for("admin_login", next=request.path))
            return fn(*args, **kwargs)
        return wrapped

    def theme_rows():
        with db() as conn:
            rows = conn.execute("""
                SELECT t.*,
                    (SELECT COUNT(*) FROM subthemes s WHERE s.theme_id=t.id) AS sub_count,
                    (SELECT COUNT(*) FROM mappings m JOIN subthemes s ON s.id=m.subtheme_id
                     WHERE s.theme_id=t.id) AS mapping_count
                FROM themes t ORDER BY t.id
            """).fetchall()
        return [dict(r) for r in rows]

    def subtheme_rows():
        with db() as conn:
            rows = conn.execute("""
                SELECT s.*,t.name AS theme_name,
                    (SELECT COUNT(*) FROM mappings m WHERE m.subtheme_id=s.id) AS mapping_count
                FROM subthemes s JOIN themes t ON t.id=s.theme_id
                ORDER BY t.id,s.id
            """).fetchall()
        return [dict(r) for r in rows]

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if session.get("admin_logged_in"):
            return redirect(url_for("admin_home"))
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if hmac.compare_digest(username, ADMIN_USERNAME) and hmac.compare_digest(password, ADMIN_PASSWORD):
                session.clear()
                session["admin_logged_in"] = True
                session["_csrf_token"] = secrets.token_urlsafe(32)
                flash("Berhasil masuk ke panel Admin.", "success")
                next_url = request.args.get("next", "")
                if next_url.startswith("/") and not next_url.startswith("//"):
                    return redirect(next_url)
                return redirect(url_for("admin_home"))
            flash("Username atau password salah.", "error")
        return render_template("admin_login.html")

    @app.post("/admin/logout")
    @admin_required
    def admin_logout():
        session.clear()
        flash("Anda sudah keluar dari Admin.", "success")
        return redirect(url_for("admin_login"))

    @app.route("/admin")
    @admin_required
    def admin_home():
        with db() as conn:
            stats = {
                "themes": conn.execute("SELECT COUNT(*) FROM themes").fetchone()[0],
                "subthemes": conn.execute("SELECT COUNT(*) FROM subthemes").fetchone()[0],
                "mappings": conn.execute("SELECT COUNT(*) FROM mappings").fetchone()[0],
                "manual": conn.execute("SELECT COUNT(*) FROM mappings WHERE source='manual'").fetchone()[0],
            }
        return render_template("admin_home.html", stats=stats)

    @app.route("/admin/tema")
    @admin_required
    def admin_themes():
        return render_template("admin_themes.html", rows=theme_rows())

    @app.route("/admin/tema/tambah", methods=["GET", "POST"])
    @app.route("/admin/tema/<int:tid>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_theme_form(tid=None):
        row = None
        if tid is not None:
            with db() as conn:
                found = conn.execute("SELECT * FROM themes WHERE id=?", (tid,)).fetchone()
            if not found:
                abort(404)
            row = dict(found)
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            if not name:
                flash("Nama tema wajib diisi.", "error")
                return render_template("admin_theme_form.html", row=row)
            try:
                with db() as conn:
                    if tid is None:
                        conn.execute("INSERT INTO themes(name,description) VALUES(?,?)", (name, description))
                    else:
                        conn.execute("UPDATE themes SET name=?,description=? WHERE id=?", (name, description, tid))
                refresh_catalog()
                flash("Tema berhasil disimpan.", "success")
                return redirect(url_for("admin_themes"))
            except sqlite3.IntegrityError:
                flash("Nama tema tersebut sudah digunakan.", "error")
        return render_template("admin_theme_form.html", row=row)

    @app.post("/admin/tema/<int:tid>/hapus")
    @admin_required
    def admin_theme_delete(tid):
        with db() as conn:
            conn.execute("DELETE FROM themes WHERE id=?", (tid,))
        refresh_catalog()
        flash("Tema dan seluruh subtema/pemetaan terkait telah dihapus.", "success")
        return redirect(url_for("admin_themes"))

    @app.route("/admin/subtema")
    @admin_required
    def admin_subthemes():
        return render_template("admin_subthemes.html", rows=subtheme_rows())

    @app.route("/admin/subtema/tambah", methods=["GET", "POST"])
    @app.route("/admin/subtema/<int:sid>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_subtheme_form(sid=None):
        row = None
        with db() as conn:
            themes = [dict(r) for r in conn.execute("SELECT id,name FROM themes ORDER BY id")]
            if sid is not None:
                found = conn.execute("SELECT * FROM subthemes WHERE id=?", (sid,)).fetchone()
                if not found:
                    abort(404)
                row = dict(found)
        if request.method == "POST":
            try:
                theme_id = int(request.form.get("theme_id", ""))
            except ValueError:
                theme_id = 0
            name = request.form.get("name", "").strip()
            keywords = list(dict.fromkeys(
                x.strip().lower() for x in request.form.get("keywords", "").split(",") if x.strip()
            ))
            if not name or theme_id not in [t["id"] for t in themes]:
                flash("Tema utama dan nama subtema wajib dipilih.", "error")
                return render_template("admin_subtheme_form.html", row=row, themes=themes)
            try:
                with db() as conn:
                    encoded = json.dumps(keywords, ensure_ascii=False)
                    if sid is None:
                        conn.execute(
                            "INSERT INTO subthemes(theme_id,name,keywords) VALUES(?,?,?)",
                            (theme_id, name, encoded)
                        )
                    else:
                        conn.execute(
                            "UPDATE subthemes SET theme_id=?,name=?,keywords=? WHERE id=?",
                            (theme_id, name, encoded, sid)
                        )
                refresh_catalog()
                flash("Subtema berhasil disimpan.", "success")
                return redirect(url_for("admin_subthemes"))
            except sqlite3.IntegrityError:
                flash("Nama subtema sudah ada pada tema tersebut.", "error")
        return render_template("admin_subtheme_form.html", row=row, themes=themes)

    @app.post("/admin/subtema/<int:sid>/hapus")
    @admin_required
    def admin_subtheme_delete(sid):
        with db() as conn:
            conn.execute("DELETE FROM subthemes WHERE id=?", (sid,))
        refresh_catalog()
        flash("Subtema dan seluruh pemetaannya telah dihapus.", "success")
        return redirect(url_for("admin_subthemes"))

    @app.route("/admin/pemetaan", methods=["GET", "POST"])
    @admin_required
    def admin_mappings():
        if request.method == "POST":
            try:
                surah = int(request.form.get("nomor_surat", ""))
                ayah = int(request.form.get("nomor_ayat", ""))
                subtheme_id = int(request.form.get("subtheme_id", ""))
            except ValueError:
                flash("Data ayat atau subtema tidak valid.", "error")
                return redirect(url_for("admin_mappings", q=request.form.get("q", "")))
            valid_verse = any(
                int(r["nomor_surat"]) == surah and int(r["nomor_ayat"]) == ayah
                for r in app_globals["AYAT"][["nomor_surat", "nomor_ayat"]].to_dict("records")
            )
            if not valid_verse:
                flash("Ayat tidak ditemukan dalam database Al-Qur'an.", "error")
            else:
                try:
                    with db() as conn:
                        conn.execute(
                            """INSERT INTO mappings(nomor_surat,nomor_ayat,subtheme_id,source)
                               VALUES(?,?,?,'manual')
                               ON CONFLICT(nomor_surat,nomor_ayat,subtheme_id)
                               DO UPDATE SET source='manual'""",
                            (surah, ayah, subtheme_id)
                        )
                        conn.execute(
                            "DELETE FROM excluded_auto WHERE nomor_surat=? AND nomor_ayat=? AND subtheme_id=?",
                            (surah, ayah, subtheme_id)
                        )
                    refresh_catalog()
                    flash("Pemetaan ayat berhasil ditambahkan.", "success")
                except sqlite3.IntegrityError:
                    flash("Subtema tidak ditemukan atau pemetaan tidak valid.", "error")
            return redirect(url_for("admin_mappings", q=request.form.get("q", "")))

        q = request.args.get("q", "").strip()
        q_lower = q.lower()
        rows = []
        if q:
            ayat_records = app_globals["AYAT"].to_dict("records")
            ref_match = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)\s*", q)
            for verse in ayat_records:
                try:
                    surah = int(verse["nomor_surat"])
                    ayah = int(verse["nomor_ayat"])
                except (TypeError, ValueError, KeyError):
                    continue
                translation = str(verse.get("terjemahan_indonesia", ""))
                arabic = str(verse.get("teks_arab", ""))
                surah_name = app_globals["NAMA_SURAT"].get(surah, "")
                matched = (
                    q_lower in translation.lower() or q_lower in arabic.lower()
                    or q_lower in surah_name.lower()
                    or (ref_match and surah == int(ref_match.group(1)) and ayah == int(ref_match.group(2)))
                )
                if matched:
                    tags = [
                        {
                            "tema": m["tema"], "subtema": m["subtema"],
                            "mapping_id": m["mapping_id"]
                        }
                        for m in app_globals["MAPPING"]
                        if m["nomor_surat"] == surah and m["nomor_ayat"] == ayah
                    ]
                    rows.append({
                        "nomor_surat": surah, "nomor_ayat": ayah,
                        "nama_surat": surah_name,
                        "teks_arab": arabic,
                        "terjemahan_indonesia": translation,
                        "tags": tags
                    })
                    if len(rows) >= 100:
                        break

        with db() as conn:
            subthemes = [
                {"id": r["id"], "name": r["name"], "theme_name": r["theme_name"]}
                for r in conn.execute("""
                    SELECT s.id,s.name,t.name AS theme_name
                    FROM subthemes s JOIN themes t ON t.id=s.theme_id
                    ORDER BY t.id,s.id
                """)
            ]
        return render_template(
            "admin_mappings.html", q=q, rows=rows, subthemes=subthemes
        )

    @app.post("/admin/pemetaan/<int:mid>/hapus")
    @admin_required
    def admin_mapping_delete(mid):
        with db() as conn:
            mapping = conn.execute("SELECT * FROM mappings WHERE id=?", (mid,)).fetchone()
            if mapping:
                if mapping["source"] == "auto":
                    conn.execute(
                        """INSERT OR IGNORE INTO excluded_auto
                           (nomor_surat,nomor_ayat,subtheme_id) VALUES(?,?,?)""",
                        (mapping["nomor_surat"], mapping["nomor_ayat"], mapping["subtheme_id"])
                    )
                conn.execute("DELETE FROM mappings WHERE id=?", (mid,))
        refresh_catalog()
        flash("Pemetaan ayat berhasil dihapus.", "success")
        return redirect(url_for("admin_mappings", q=request.form.get("q", "")))

    init_db()
    refresh_catalog()
