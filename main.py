from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from datetime import timedelta
import os
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static/img')
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024  # Ограничение на размер файла в 16 МБ
app.config['SECRET_KEY'] = 'your_secret_key'

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
csrf.init_app(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=1)

@app.route('/')
def index():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)

@app.route('/admin')
def admin():
    posts = Post.query.order_by(Post.id.desc()).all()
    items = Item.query.order_by(Item.id.desc()).all()
    return render_template('admin.html', posts=posts, items=items)

@app.route('/admin/add', methods=['GET', 'POST'])
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files.get('image_or_video')
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'img/{filename}')
        else:
            image_url = None
        new_post = Post(title=title, content=content, image_url=image_url)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('add_post.html')

@app.route('/admin/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        image = request.files.get('image')
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'img/{filename}')
        else:
            image_url = None
        new_item = Item(name=name, price=price, description=description, image_url=image_url)
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('add_item.html')

@app.route('/admin/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Пост успешно удален!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Товар успешно удален!', 'success')
    return redirect(url_for('admin'))

@app.route('/shop')
def shop():
    items = Item.query.order_by(Item.id.desc()).all()
    return render_template('shop.html', items=items)

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)

@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    item = Item.query.get_or_404(item_id)
    cart = session.get('cart', {})

    # Ensure keys and values are integers
    cart = {int(k): int(v) for k, v in cart.items()}

    cart[item_id] = cart.get(item_id, 0) + 1
    session['cart'] = cart
    session['cart_count'] = sum(cart.values())
    flash(f'Товар {item.name} добавлен в корзину!', 'success')

    # Redirect back to the shop with the item_id as a URL parameter
    return redirect(url_for('shop', _anchor=f'item_{item_id}'))


@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    items = Item.query.filter(Item.id.in_(cart.keys())).all()

    # Преобразуем ключи в строковые значения для корректного доступа в шаблоне
    cart_str_keys = {str(k): v for k, v in cart.items()}

    # Вычисляем итоговую стоимость
    total_cost = sum(item.price * cart_str_keys[str(item.id)] for item in items)

    return render_template('cart.html', items=items, cart=cart_str_keys, total_cost=total_cost, str=str)

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart = session.get('cart', {})
    item_id_str = str(item_id)
    if item_id_str in cart:
        if cart[item_id_str] > 1:
            cart[item_id_str] -= 1
        else:
            del cart[item_id_str]
        session['cart'] = cart
        session['cart_count'] = sum(cart.values())
        flash('Товар удален из корзины!', 'success')
    return redirect(url_for('cart'))




@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        # Здесь можно добавить логику для обработки данных формы
        flash('Спасибо за ваше сообщение! Мы свяжемся с вами в ближайшее время.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/main_menu')
def main_menu():
    items = Item.query.order_by(Item.id.desc()).all()
    return render_template('main_menu.html', items=items)


@app.route('/ready')
def ready():
    name = request.args.get('name')
    phone = request.args.get('phone')
    items = request.args.getlist('items')
    return render_template('ready.html', name=name, phone=phone, items=items)

@app.route('/place_order', methods=['POST'])
def place_order():
    name = request.form['name']
    phone = request.form['phone']
    cart = session.get('cart', {})
    items = Item.query.filter(Item.id.in_(cart.keys())).all()

    order_details = f"Заказ от {name} Номер-{phone}:\n\n"
    ordered_items = []
    for item in items:
        quantity = cart[str(item.id)]
        order_details += f">>>{item.name} - {quantity} шт. - {item.price * quantity} грн\n"
        ordered_items.append(item.name)
    order_details += f"\nИтоговая стоимость: {sum(item.price * cart[str(item.id)] for item in items)} грн"

    # Отправка сообщения в Telegram
    telegram_bot_token = '6709819658:AAGT9kOdC0qrbrm4-yjuyqt-_Kj8JwGzAz0'
    telegram_chat_id = '6547378362'
    telegram_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    requests.post(telegram_url, data={'chat_id': telegram_chat_id, 'text': order_details})

    flash('Заказ успешно оформлен! Мы свяжемся с вами в ближайшее время.', 'success')
    session.pop('cart', None)  # Очистить корзину после заказа
    session.pop('cart_count', None)  # Обновить количество товаров в корзине
    return redirect(url_for('ready', name=name, phone=phone, items=ordered_items))


@app.route('/process_order2', methods=['POST'])
def process_order2():
    item_id = request.form['item_id']
    name = request.form['name']
    phone = request.form['phone']

    item = Item.query.get_or_404(item_id)

    order_details = f"Покупка от {name} (Телефон: {phone}):\n\n"
    order_details += f"{item.name} - {item.price} грн\n"

    # Отправка сообщения в Telegram
    telegram_bot_token = '6709819658:AAGT9kOdC0qrbrm4-yjuyqt-_Kj8JwGzAz0'
    telegram_chat_id = '6547378362'
    telegram_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    requests.post(telegram_url, data={'chat_id': telegram_chat_id, 'text': order_details})

    flash('Покупка успешно оформлена! Мы свяжемся с вами в ближайшее время.', 'success')
    return redirect(url_for('ready', name=name, phone=phone, items=[item.name]))




@app.route('/bay_now', methods=['POST'])
def bay_now():
    item_id = request.form['item_id']
    name = request.form['name']
    phone = request.form['phone']

    item = Item.query.get_or_404(item_id)

    order_details = f"Покупка от {name} (Телефон: {phone}):\n\n"
    order_details += f"{item.name} - {item.price} грн\n"

    # Отправка сообщения в Telegram
    telegram_bot_token = '6709819658:AAGT9kOdC0qrbrm4-yjuyqt-_Kj8JwGzAz0'
    telegram_chat_id = '6547378362'
    telegram_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    requests.post(telegram_url, data={'chat_id': telegram_chat_id, 'text': order_details})

    flash('Покупка успешно оформлена! Мы свяжемся с вами в ближайшее время.', 'success')
    return redirect(url_for('shop'))


@app.route('/email_send', methods=['POST'])
def email_send():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        # Формируем сообщение для отправки в Telegram
        telegram_message = f"Сообщение от {name} ({email}):\n\n{message}"

        # Отправляем сообщение в Telegram
        telegram_bot_token = '6709819658:AAGT9kOdC0qrbrm4-yjuyqt-_Kj8JwGzAz0'
        telegram_chat_id = '6547378362'
        telegram_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        requests.post(telegram_url, data={'chat_id': telegram_chat_id, 'text': telegram_message})

        flash('Ваше сообщение успешно отправлено!', 'success')
        return redirect(url_for('main_menu'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8000, debug=True)