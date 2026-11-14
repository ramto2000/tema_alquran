from flask import Flask, render_template, request, send_file, abort
from pathlib import Path
import pandas as pd
import re, io, os
import re
import unicodedata
from markupsafe import Markup, escape


def normalize_search(text):
    """Menormalkan teks agar pencarian tidak terganggu tanda baca."""
    text = str(text or "").casefold()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def highlight_text(text, keyword):
    text = str(text or "")
    keyword = str(keyword or "").strip()

    if not keyword:
        return escape(text)

    # Ambil kata-kata pencarian
    words = normalize_search(keyword).split()

    if not words:
        return escape(text)

    # Sorot setiap kata yang dicari
    pattern = re.compile(
        "|".join(re.escape(w) for w in sorted(set(words), key=len, reverse=True)),
        re.IGNORECASE
    )

    parts = []
    last = 0

    for match in pattern.finditer(text):
        parts.append(escape(text[last:match.start()]))

        parts.append(
            Markup('<mark class="highlight-kata">')
            + escape(match.group())
            + Markup('</mark>')
        )

        last = match.end()

    parts.append(escape(text[last:]))

    return Markup("").join(parts)
    
BASE = Path(__file__).resolve().parent
EXCEL_PATH = Path(os.environ.get('ALQURAN_EXCEL', BASE / 'alquran_terjemahan.xlsx'))
app = Flask(__name__)
app.jinja_env.filters["highlight"] = highlight_text
THEMES = [
(1,'Tauhid dan Keimanan','Mengenal Allah, mengesakan-Nya, dan membangun keyakinan yang benar.',[
('Ke-esaan dan kekuasaan Allah',['maha esa','tidak ada tuhan selain allah','allah tuhan','tuhan yang esa','pencipta langit dan bumi']),('Sifat dan nama Allah',['maha pengasih','maha penyayang','maha mengetahui','maha kuasa','maha mendengar','maha melihat']),('Iman dan perkara gaib',['orang-orang yang beriman','beriman kepada allah','hari akhir','hari kemudian','malaikat']),('Syirik dan kekufuran',['mempersekutukan allah','menyekutukan allah','selain allah','orang-orang kafir','tidak beriman'])]),
(2,'Al-Qur’an, Wahyu, dan Kenabian','Al-Qur’an sebagai petunjuk dan tugas para rasul menyampaikan wahyu.',[
('Al-Qur’an sebagai petunjuk',['al-qur’an','kitab yang diturunkan','petunjuk bagi','ayat-ayat kami']),('Wahyu dan kitab suci',['wahyu','kitab taurat','kitab injil','lembaran-lembaran']),('Rasul dan tugas dakwah',['rasul','para nabi','utusan allah','menyampaikan risalah']),('Kebenaran wahyu',['diturunkan kepadamu','membacakan ayat-ayat','peringatan'])]),
(3,'Ibadah dan Penghambaan kepada Allah','Bentuk pengabdian manusia kepada Allah dalam kehidupan.',[
('Shalat',['shalat','mendirikan salat','sujud','ruku']),('Puasa',['puasa','berpuasalah','bulan ramadan']),('Zakat, infak, dan sedekah',['zakat','infakkan','menginfakkan','sedekah','memberikan harta']),('Haji dan umrah',['haji','umrah','baitullah','ka’bah']),('Doa, zikir, dan ibadah',['berdoalah','berzikirlah','mengingat allah','sembahlah allah'])]),
(4,'Akhlak dan Pembentukan Karakter','Pembentukan pribadi yang berakhlak mulia.',[
('Sabar dan syukur',['bersabarlah','orang-orang yang sabar','bersyukur','mensyukuri']),('Jujur dan menepati janji',['jujur','orang-orang yang benar','menepati janji','penuhilah janji']),('Rendah hati dan tidak sombong',['janganlah sombong','kesombongan','rendah hati','berjalan di bumi']),('Menjaga lisan dan hati',['menggunjing','mengolok-olok','prasangka','iri hati','amarah']),('Ikhlas dan tawakal',['ikhlas','bertawakallah','bertawakal kepada allah'])]),
(5,'Keluarga, Pernikahan, dan Keturunan','Pedoman membangun keluarga dan menjaga hak anggota keluarga.',[
('Pernikahan dan pasangan',['menikah','nikah','istri-istri','suami','pasangan']),('Hak dan kewajiban keluarga',['mahar','nafkah','talak','perceraian']),('Orang tua dan anak',['kedua orang tua','ibu bapak','anak-anakmu','menyusui']),('Kerabat dan warisan',['warisan','ahli waris','kerabat','anak yatim'])]),
(6,'Keadilan, Hukum, dan Tanggung Jawab','Ketentuan untuk menegakkan keadilan dan menjaga amanah.',[
('Keadilan dan persaksian',['berlaku adil','keadilan','persaksian','saksi']),('Amanah dan perjanjian',['amanat','amanah','perjanjian','menunaikan amanah']),('Hukum dan ketentuan',['hukum','ditetapkan allah','ketentuan allah','hukuman']),('Larangan zalim',['berbuat zalim','orang-orang zalim','kezaliman','melampaui batas'])]),
(7,'Ekonomi, Harta, dan Muamalah','Pedoman memperoleh dan menggunakan harta secara benar.',[
('Rezeki dan usaha',['rezeki','mencari karunia','berusaha','perniagaan']),('Jual beli dan riba',['jual beli','riba','menghalalkan jual beli']),('Utang piutang',['utang','piutang','berutang','mencatat utang']),('Infak dan distribusi harta',['harta benda','fakir miskin','orang miskin','infakkan harta']),('Larangan harta batil',['memakan harta','harta dengan jalan yang batil','curang'])]),
(8,'Ilmu Pengetahuan dan Pemikiran','Dorongan menggunakan akal dan mengambil pelajaran dari tanda-tanda kebesaran Allah.',[
('Keutamaan ilmu',['orang-orang yang berilmu','ilmu','pengetahuan','mengajarkan']),('Berpikir dan merenung',['berpikir','memikirkan','orang-orang yang berakal','mengambil pelajaran']),('Mengamati alam',['memperhatikan','lihatlah','tanda-tanda kekuasaan','langit dan bumi']),('Hikmah dan pemahaman',['hikmah','memahami','mengetahui'])]),
(9,'Sejarah dan Kisah Para Nabi','Pelajaran dari perjalanan para nabi dan umat terdahulu.',[
('Kisah para nabi',['adam','nuh','ibrahim','musa','yusuf','daud','sulaiman','isa','muhammad']),('Bani Israil dan umat terdahulu',['bani israil','kaum ‘ad','kaum tsamud','fir’aun','umat terdahulu']),('Pelajaran dari sejarah',['kisah','cerita mereka','negeri-negeri','dibinasakan umat'])]),
(10,'Setan, Dosa, dan Penyimpangan Manusia','Mengenali godaan, dosa, dan perilaku yang menyesatkan.',[
('Iblis dan godaan setan',['iblis','setan','syaitan','menggoda']),('Munafik dan kufur',['orang-orang munafik','munafik','orang-orang kafir','mengingkari']),('Dosa dan maksiat',['berbuat dosa','kemaksiatan','perbuatan keji','dosa']),('Kerusakan dan kesombongan',['kerusakan di bumi','membuat kerusakan','sombong','melampaui batas'])]),
(11,'Taubat, Ampunan, dan Kasih Sayang Allah','Kesempatan kembali kepada Allah dan memperoleh rahmat-Nya.',[
('Taubat dan kembali kepada Allah',['bertaubat','taubat','kembali kepada allah']),('Ampunan dan penghapusan dosa',['mengampuni dosa','ampunan','menghapus kesalahan']),('Rahmat dan kasih sayang Allah',['rahmat allah','maha pengampun','maha penerima taubat']),('Tidak berputus asa',['jangan berputus asa','berputus asa dari rahmat'])]),
(12,'Kehidupan Dunia, Kematian, dan Akhirat','Hakikat kehidupan dan pertanggungjawaban setelah kematian.',[
('Kehidupan dunia',['kehidupan dunia','kesenangan dunia','perhiasan dunia']),('Kematian dan kebangkitan',['kematian','mati','dibangkitkan','hari kebangkitan']),('Hari kiamat dan perhitungan',['hari kiamat','hari pembalasan','hisab','timbangan amal']),('Surga dan neraka',['surga','jannah','neraka','neraka jahannam','azab'])]),
(13,'Penciptaan dan Alam Semesta','Tanda kekuasaan Allah dalam penciptaan dan pengaturan alam.',[
('Penciptaan langit dan bumi',['menciptakan langit','bumi dan langit','penciptaan langit']),('Matahari, bulan, dan malam',['matahari','bulan','bintang','siang dan malam']),('Air, hujan, dan tumbuhan',['air hujan','hujan','air dari langit','tumbuh-tumbuhan']),('Hewan dan gunung',['hewan','binatang ternak','gunung','lautan','laut'])]),
(14,'Perjuangan, Perdamaian, dan Hubungan Antarkelompok','Pedoman menghadapi konflik, menjaga persatuan, dan membangun perdamaian.',[
('Jihad dan perjuangan',['berjihad','jihad','berperang di jalan allah']),('Perang dan pertahanan',['perang','berperang','musuh','peperangan']),('Perdamaian dan rekonsiliasi',['perdamaian','berdamai','perdamaikan','cenderung kepada perdamaian']),('Hijrah dan persatuan',['berhijrah','muhajirin','persaudaraan','bersatu'])]),
(15,'Kemanusiaan dan Kepedulian Sosial','Tanggung jawab terhadap sesama dan masyarakat.',[
('Fakir miskin dan anak yatim',['anak yatim','fakir miskin','orang miskin']),('Menolong dan berbuat baik',['tolong-menolong','berbuat baik','menolong','memberi makan']),('Persaudaraan dan kesetaraan',['bersaudara','persaudaraan','suku-suku','bangsa-bangsa']),('Hak sesama manusia',['tetangga','musafir','orang yang membutuhkan','menghormati'])]),
(16,'Doa, Zikir, dan Ketergantungan kepada Allah','Hubungan spiritual manusia dengan Allah dalam segala keadaan.',[
('Memohon petunjuk dan kebaikan',['tunjukilah kami','jalan yang lurus','berilah kami']),('Doa dan permohonan',['berdoa','berdoalah','memohon kepada allah']),('Zikir dan mengingat Allah',['mengingat allah','berzikirlah','menyebut nama allah']),('Perlindungan dan tawakal',['berlindung kepada','lindungilah','bertawakal'])])
]

def load_data():
    if not EXCEL_PATH.exists(): raise FileNotFoundError(f'File Excel tidak ditemukan: {EXCEL_PATH}')
    xls = pd.ExcelFile(EXCEL_PATH)
    ay = pd.read_excel(EXCEL_PATH, sheet_name='Ayat').fillna('')
    su = pd.read_excel(EXCEL_PATH, sheet_name='Surat').fillna('')
    required={'nomor_surat','nomor_ayat','terjemahan_indonesia','teks_arab'}
    if not required.issubset(ay.columns): raise ValueError('Kolom wajib pada sheet Ayat tidak lengkap: '+', '.join(sorted(required-set(ay.columns))))
    names={int(r.nomor_surat):str(r.nama_latin) for r in su.itertuples()}
    return ay, su, names

AYAT, SURAT, NAMA_SURAT = load_data()

def classify(text):
    t=str(text).lower().replace('’',"'")
    found=[]
    for tid,tname,desc,subs in THEMES:
        for sname,keywords in subs:
            hits=[k for k in keywords if k in t]
            if hits: found.append((tid,tname,sname,', '.join(hits[:3])))
    return found

MAPPING=[]
for row in AYAT.to_dict('records'):
    matches=classify(row.get('terjemahan_indonesia',''))
    for tid,tname,sname,hits in matches:
        MAPPING.append({'nomor_global':row.get('nomor_global',''),'nomor_surat':int(row['nomor_surat']),'nama_surat':NAMA_SURAT.get(int(row['nomor_surat']),''),'nomor_ayat':int(row['nomor_ayat']),'teks_arab':row.get('teks_arab',''),'terjemahan_indonesia':row.get('terjemahan_indonesia',''),'id_tema':tid,'tema':tname,'subtema':sname,'kata_pemicu':hits})

@app.template_filter('ref')
def ref(n,a): return f'{int(n)}:{int(a)}'

@app.route('/')
def index():
    q=request.args.get('q','').strip().lower()
    theme_count=len(THEMES); verse_count=len(AYAT); mapped=len(set((m['nomor_surat'],m['nomor_ayat']) for m in MAPPING))
    themes=[]
    for tid,name,desc,subs in THEMES:
        rows=[m for m in MAPPING if m['id_tema']==tid]
        if q and q not in name.lower() and q not in desc.lower() and not any(q in s[0].lower() for s in subs): continue
        themes.append({'id':tid,'name':name,'desc':desc,'subcount':len(subs),'count':len(rows),'verses':len(set((m['nomor_surat'],m['nomor_ayat']) for m in rows))})
    return render_template('index.html',themes=themes,q=q,verse_count=verse_count,theme_count=theme_count,mapped=mapped,sub_count=sum(len(t[3]) for t in THEMES))

@app.route('/tema/<int:tid>')
def tema_detail(tid):
    theme=next((t for t in THEMES if t[0]==tid),None)
    if not theme: abort(404)
    sub=request.args.get('sub','')
    q=request.args.get('q','').strip().lower()
    rows=[m for m in MAPPING if m['id_tema']==tid and (not sub or m['subtema']==sub)]
    if q: rows=[m for m in rows if q in str(m['terjemahan_indonesia']).lower() or q in str(m['nama_surat']).lower()]
    return render_template('tema.html',theme=theme,rows=rows,selected=sub,q=q,subthemes=[s[0] for s in theme[3]])

@app.route('/cari')
def cari():
    q = request.args.get('q', '').strip()
    words = normalize_search(q).split()

    rows = []

    if words:
        for r in AYAT.to_dict('records'):

            terjemahan = str(
                r.get('terjemahan_indonesia', '') or ''
            )

            arab = str(
                r.get('teks_arab', '') or ''
            )

            # Normalisasi isi ayat
            teks_normal = normalize_search(terjemahan)
            arab_normal = normalize_search(arab)

            # Semua kata harus ditemukan dalam satu ayat
            cocok_terjemahan = all(
                word in teks_normal for word in words
            )

            cocok_arab = all(
                word in arab_normal for word in words
            )

            if not (cocok_terjemahan or cocok_arab):
                continue

            n = int(r['nomor_surat'])
            a = int(r['nomor_ayat'])

            tags = [
                {
                    'tema': m['tema'],
                    'subtema': m['subtema'],
                    'id': m['id_tema']
                }
                for m in MAPPING
                if m['nomor_surat'] == n
                and m['nomor_ayat'] == a
            ]

            rows.append({
                'n': n,
                'a': a,
                'surat': NAMA_SURAT.get(n, ''),
                'arab': arab,
                'translation': terjemahan,
                'tags': tags
            })

        rows = rows[:300]

    return render_template(
        'cari.html',
        q=q,
        rows=rows
    )

@app.route('/ekspor')
def ekspor():
    df=pd.DataFrame(MAPPING)
    if df.empty: abort(404)
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine='openpyxl') as writer:
        pd.DataFrame([{'id_tema':t[0],'nama_tema':t[1],'deskripsi':t[2]} for t in THEMES]).to_excel(writer,index=False,sheet_name='Tema_Utama')
        pd.DataFrame([{'id_tema':t[0],'nama_tema':t[1],'nama_subtema':s[0]} for t in THEMES for s in t[3]]).to_excel(writer,index=False,sheet_name='Subtema')
        df.to_excel(writer,index=False,sheet_name='Pemetaan_Ayat')
    out.seek(0)
    return send_file(out,as_attachment=True,download_name='pemetaan_tema_alquran.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/tentang')
def tentang(): return render_template('tentang.html')
import admin_extension
admin_extension.register_admin(app, globals())

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5001)),debug=True)
