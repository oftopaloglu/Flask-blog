from flask import Flask, render_template, redirect, url_for, session, logging, request, flash
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

# Kullanıcı giriş decorator


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Görüntülemek için giriş yap.", "warning")
            return redirect(url_for("login"))
    return decorated_function

# Kayıt formu


class RegisterForm(Form):
    name = StringField("Ad Soyad", validators=[validators.Length(
        min=4, max=25, message="En az 4 en çok 25 damga uzunluğunda olmalı.")])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(
        min=5, max=35, message="En az 5 en çok 35 damga uzunluğunda olmalı.")])
    email = StringField(
        "E-Posta", validators=[validators.Email(message="Geçerli bir e-posta adresi giriniz.")])
    password = PasswordField("Şifre", validators=[
        validators.DataRequired(message="Lütfen bir şifre girin."),
        validators.EqualTo(fieldname="confirm", message="Şifre uyuşmuyor.")
    ])
    confirm = PasswordField("Şifre doğrula.")


class LoginForm(Form):
    username = StringField("Kullanıcı Adı:")
    password = PasswordField("Şifre:")


app = Flask(__name__)

app.secret_key = "blog"

app.config["MYSQL_HOST"] = "127.0.0.1"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")

# Kayıt olma
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "Insert into users(name,username,email,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(sorgu, (name, username, email, password))
        mysql.connection.commit()

        cursor.close()

        flash("Kaydolundu.", "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)

# Giriş yap
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()

        sorgu = "Select * From users where username = %s"

        result = cursor.execute(sorgu, (username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]

            if sha256_crypt.verify(password_entered, real_password):
                flash("Giriş başarılı.", "success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Yanlış şifre.", "danger")
                return redirect(url_for("login"))

        else:
            flash("Geçersiz kullanıcı adı.", "danger")
            return redirect(url_for("login"))

    else:
        return render_template("login.html", form=form)

# Çıkış
@app.route("/logout")
def logout():
    session.clear()
    flash("Çıkış Yapıldı.", "dark")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where author = %s"

    result = cursor.execute(sorgu, (session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles=articles)
    else:
        return render_template("dashboard.html")

    return render_template("dashboard.html")

# Makale ekle
@app.route("/addarticle", methods=["GET", "POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(sorgu, (title, session["username"], content))

        mysql.connection.commit()

        cursor.close()

        flash("Makale eklendi.", "success") 

        return redirect(url_for("dashboard"))

    return render_template("addarticle.html", form=form)

# Makale form


class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[
                        validators.Length(min=5, max=100)])
    content = TextAreaField("İçerik", validators=[validators.Length(min=10)])

# Makale sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles"

    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles=articles)
    else:
        return render_template("articles.html")

# Makale içeriği
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * from articles where id = %s"

    result = cursor.execute(sorgu, (id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article=article)
    else:
        return render_template("article.html")

# Makale sil
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * from articles where author = %s and id = %s"

    result = cursor.execute(sorgu, (session["username"], id))

    if result > 0:
        sorgu2 = "Delete from articles where id = %s"

        cursor.execute(sorgu2, (id,))

        mysql.connection.commit()

        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya silme yetkiniz yok.", "danger")
        return redirect(url_for("index"))

# Makale düzenle
@app.route("/edit/<string:id>", methods=["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()

        sorgu = "Select * from articles where id = %s and author = %s"

        result = cursor.execute(sorgu, (id, session["username"]))

        if result == 0:
            flash("Böyle bir makale yok veya işlem yetkiniz yok.", "danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]

            return render_template("update.html", form=form)
    else:
        # POST request
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "Update articles Set title = %s, content = %s where id = %s"

        cursor = mysql.connection.cursor()

        cursor.execute(sorgu2, (newTitle, newContent, id))

        mysql.connection.commit()

        flash("Güncellendi", "info")

        return redirect(url_for("dashboard"))

# Ara
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        sorgu = "Select * from articles where title like '%" + keyword + "%' "

        result = cursor.execute(sorgu)

        if result == 0:
            flash("Sonuç yok", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles=articles)


if __name__ == "__main__":
    app.run(debug=True)
