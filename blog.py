from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps


# User Login Decoratar
def login_required(f):  # Buradaki f login_required ın decorator olarak öncesinde kullanıldığı fonksiyon bizim için dashboard
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged in" in session:  # Login i biz session ile oluşturuyoruz, eğer giriş yapıldıysa direk dashboarda gidebilmeli
            return f(*args, **kwargs)  # Bu pek alakalı gelemeye bilir fakat burada basit bir şekilde kontrol edilen fonksiyonun göndermeye çalıştığı urlye yönlendiriyor sanırım.
        else:  # Login yapılmadıysa login sayfasına yönlendiriyor.
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.", "danger")
            return redirect(url_for("login"))
    return decorated_function  # login_required çağrıldığında decorated_function çağırılmadığı için çalışmayacak sadece tanımlanacak, çalışması için çağırıyor.

# Register form
class RegistForm(Form):
    name = StringField("İsim Soyisim:", validators=[validators.length(min=4, max=25),])  # Bu olay baya güzel, girilen verinin nasıl girileceğini vb kontrol edebiliyoruz. Bunda basit minmax karakter kontrol ediliyor.
    username = StringField("Kullanıcı Adı:", validators=[validators.length(min=5, max=30)])
    email = StringField("Email Adresi:", validators=[validators.Email(message="Lütfen geçerli bir email adresi girin.")])  # Burada email olması kontrol ediliyor.
    password = PasswordField("Parola:", validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin."),
        validators.EqualTo(fieldname="confirm", message="Paralonız eşleşmiyor.")
    ])
    confirm = PasswordField("Parola Kontrolü:")

# Login form
class LoginForm(Form):
    username = StringField("Kullanıcı Adı:")
    password = PasswordField("Parola:")

# Article Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.length(min = 5, max = 100)])
    content = TextAreaField("Makale İçeriği", validators=[validators.length(min = 10)])


app = Flask(__name__)
app.secret_key = "ybblog"

# Aşağıda yaptığımız app.config işlemleri Flask ile MySQL veri tabanın bağlantısını sağlamak için gerekli.
app.config["MYSQL_HOST"] = "localhost"  # Ayrı bir sunucu olsaydı onun adresini verecektik
app.config["MYSQL_USER"] = "root"  # Xampp ilk kurulduğunda varsayılan şekilde user root geliyor
app.config["MYSQL_PASSWORD"] = ""  # Paraloda boş geliyor.
app.config["MYSQL_DB"] = "ybblog"  # Oluşturduğumuz veri tabanın ismi
app.config["MYSQL_CURSORCLASS"] = "DictCursor"  # Bu önemli, verileri dbden çekerken düzenli olmasını ve sözlük olarak gelmesini istiyoruz, veri üzerinde bunu sağlamak için DictCursorı oluşturduk.

mysql = MySQL(app)  # Bizim oluşturduğumuz app i vermemiz gerekiyor, vermeseydik none olurdu.

# Main page
@app.route("/")
def index():
    return render_template("index2.html")

# About
@app.route("/about")
def about():
    return render_template("about.html")

# Articles
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()

        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

# Profile
@app.route("/profile")
@login_required
def profile():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM users WHERE username = %s"
    cursor.execute(sorgu, (session["username"], ))
    user = cursor.fetchone()
    cursor.close()

    return render_template("profile.html", user = user)

# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(sorgu, (session["username"], ))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")

# Register
@app.route("/register", methods = ["GET", "POST"])  # Burada aşağıda 167 de bahsettiğimiz request muhabbeti var, iki türlüde olabileceğini belirtiyoruz.
def register():
    form = RegistForm(request.form)  # Request tipini de form içine ekliyor
    
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)"
        cursor.execute(sorgu, (name, email, username, password))
        mysql.connection.commit()
        cursor.close()

        flash("Kayıt olma işlemi tamamlandı.", "success")

        return redirect(url_for("login")) # Burada index ile alakalı olan route a yani maine dönüyoruz. bunun için iki farklı fonk kullanılıyor redirect ve url_for
    else:
        return render_template("register.html", form = form)

# Login
@app.route("/login", methods = ["GET", "POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(sorgu, (username,))

        if result > 0:
            data = cursor.fetchone()
            password_real = data["password"]

            if sha256_crypt.verify(password_entered, password_real):
                flash("Giriş yapıldı.", "success")

                session["logged in"] = True  # Session giriş yapıldığında oturumun oluşturulması için gerekli, sözlüğe benzer kontrolleri var bu eklemede o zaten.
                session["username"] = username  # Bu ikisini yaptığımızda session başladı fakat interface de bundan kaynaklı değişiklikler yapmalıyız. Navbarda bu session değerini kullanarak arayüzde değişikler yaptık.
                
                return redirect(url_for("index"))
            else:
                flash("Hatalı şifre girildi.", "danger")
                return redirect(url_for("login"))

        else:
            flash("Hatalı kullanıcı adı girildi.", "danger")
            return redirect(url_for("login"))
    
    else:
        return render_template("login.html", form = form)

# Logout
@app.route("/logout")
def logout():
    session.clear()

    return redirect(url_for("index"))

# Add article
@app.route("/addarticle", methods = ["GET", "POST"])
def addarticle():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "INSERT INTO articles(title, author, content) VALUES(%s, %s, %s)"
        cursor.execute(sorgu, (title, session["username"], content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale girişi tamamlandı.", "success")
        return redirect(url_for("dashboard"))
    else:
        return render_template("addarticle.html", form = form)

# Delete Article
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"
    result = cursor.execute(sorgu, (session["username"], id))

    if result > 0:
        article = cursor.fetchone()
        sorgu2 = "DELETE FROM articles WHERE id = %s"
        cursor.execute(sorgu2, (id, ))
        mysql.connection.commit()
        
        flash("{} başlıklı makale silindi.".format(article["title"]), "success")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir mekale yok veya bu işleme yetkiniz yok.", "danger")
        return redirect(url_for("index"))

# Update Article
@app.route("/update/<string:id>", methods = ["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE author = %s and id = %s"
        result = cursor.execute(sorgu, (session["username"], id))

        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok.", "danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()  # Normalde formaları request.form ile oluşturuyorduk, bu sefer dbden aldığımız article ile dolduracağımız için yazmayacağız.

            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]

            return render_template("update.html", form = form)
    else:
        # Post Request
        form = ArticleForm(request.form)

        new_title = form.title.data
        new_content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu2 = "UPDATE articles SET title = %s, content = %s WHERE id = %s"
        cursor.execute(sorgu2, (new_title, new_content, id))
        mysql.connection.commit()

        flash("Makale başarıyla güncellendi.", "success")
        return redirect(url_for("dashboard"))

# Article Detail
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE id = %s"
    result = cursor.execute(sorgu, (id, ))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")

# Search URL
@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        # Post
        keyword = request.form.get("keyword")  # articles içindeki search barda input barının ismi keyword, request.from.get() ile bunun içindeki veriyi alabiliriz.

        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE title LIKE '%" + keyword + "%'"  # Bunun normal kullanımı "SELECT * FROM articles WHERE title LIKE '%mur%'", mur aranan kelime oluyor. Search bara girilen keywordü kullandık.
        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranana kelimeye uygun makale bulunumadı.", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()

            return render_template("articles.html", articles = articles)

if __name__ == "__main__":
    app.run(debug=True)


"""
Bu kısımda bootstrap adlı bir css kütüphanesini kullanacağız. Burada bulunan örnekleri alarak web sitesi geliştireceğiz. 


Dinamik urllerden bahsederken aşağdaki fonksiyonu oluşturduk, gerekli olur diye kalsın.
@app.route("/article/<string:id>")
def detail(id):
    return "Article Id: " + id

164. videoda Flask ile Mysql arasında bağlanıtıyı tanımlamak için msqldb diye bir modül indirdik ve form classlarını oluşturmak için WTF diye bir modül dahil ettik. Bunları command terminalden yaptık basit baya.
Ek olarak kullanıcı veri tablosundaki paroların şifrelenmesi için passlib modülünü indirdik. Yukarıda dahil ettik görülebilir.

167. videoda önemli bir noktaya değindik. Register işlemini siteye template olarak yansıtmaya çalışırken bahsi geçti. Html sayfalarında çokça kullanılan iki tip request var get ve post. Get request yapınca sv bunu
anlayıp sayfanın html içeriğini döndürüyor. Post request ise bir formu submitlediğimizde oluşacak http request türü. Bİr fonk çalışacaksaa fonk içerisindeki request tipini anlamamız gerekiyor. Bunun için yukarıda
flasktan importladığımız requesti kullanabiliriz. 

169 da message flashing üzerine çalışacağız, buradaki amaç kullanıcıya çeşitli eylemlerden sonra feedback vermek. Kayıt olmak sonunda gibi. Bu kısım bi tık karışık messages layout blog derken baya atlıyoruz her yere.
Ama anladığım kadarıyla includes üzerinde genel flashlar için çalışması için messages.html i oluşturduk. Bunu incelersek spesifik ne yazacağını belirlemediğini görüyoruz. Bir mesaj varsa çalışacak bu sadece. Bunu 
taşımak içinse her şeyin base i olarak kullanıdığımz layout a include ile messages.htmli ekledik. yukarıda da flash fonksiyonu ile mesaj ve kategori oluşturduk, aşağısnda da redirect(url_for) ile ana sayfaya dönecek 
bu da layoutu o da messages ı çalıştıracak. Elde bir mesaj olduğu için flashlama başarılı olacak. Sonrasında hata aldık, detayını bilmiyorum ama flash kullanabilmek için uygulamanın secret_keyi olması gerekli

Bunu messages.html içine yazdım, orada hata çıkıyor comment satırı yazareken; <!-- Buradaki with while a baya benzer. Burada divisionı bootstrap 4 alert örneklerinden ekledik, classına göre görünüşü olumlu/olumsuz 
değişim gösteriyor biz de direkt kategorimizi kullandık (success). "" içinde de {{}} ile python değişkenlerini kullanabiliyoruz.  -->

174de yukarıdaki User Login Decoratorı ekledik, bunu öncesinde ben de düşünmüştüm. Amaç giriş yapılmadığında yani session başlamadığında url üzerinden direk dashboard a gidilmesini engellemek. Bunun için dashboard 
fonksiyonundan önce bir decorator ile kontrol yapacağız. Bunun güzelliği decorator sayesinde kullanıcı giriş kontrolü için hep bunu kullanabiliriz. Kod tekrarını engelliyor.

186 ile birlikte YB Blog tamamlandı benim ekleyebileceğim şeyler; Profil sayfası oluşturmak, profil fotosu ekleme özelliği, makalelere yorum ekleme, kişi arama?
"""
