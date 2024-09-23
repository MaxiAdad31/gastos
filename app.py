from flask import Flask, make_response, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta, date  # Modifica esta línea
from sqlalchemy.sql import func  # Añade esta línea
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gastos.db'
app.config['SECRET_KEY'] = 'una_clave_secreta_muy_segura'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    gastos = db.relationship('Gasto', backref='categoria', lazy=True)

class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    importe = db.Column(db.Float, nullable=False)
    concepto = db.Column(db.String(200), nullable=False)  # Renombrado de 'descripcion' a 'concepto'
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    informacion_adicional = db.Column(db.Text, nullable=True)  # Nuevo campo opcional para texto libre

    @property
    def fecha_formateada(self):
        if isinstance(self.fecha, date):
            return self.fecha.isoformat()
        elif isinstance(self.fecha, datetime):
            return self.fecha.date().isoformat()
        elif isinstance(self.fecha, str):
            try:
                return datetime.strptime(self.fecha, '%Y-%m-%d').date().isoformat()
            except ValueError:
                return self.fecha
        else:
            return 'Fecha no válida'

class Ingreso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    importe = db.Column(db.Float, nullable=False)
    concepto = db.Column(db.String(200), nullable=False)
    detalle = db.Column(db.Text, nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    usuario = db.relationship('Usuario', backref=db.backref('ingresos', lazy=True))

    def __repr__(self):
        return f'<Ingreso {self.concepto}>'

class GastoTarjeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    concepto = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    cuota = db.Column(db.String(5), nullable=True)
    tarjeta_id = db.Column(db.Integer, db.ForeignKey('tarjeta.id'), nullable=False)
    tarjeta = db.relationship('Tarjeta', backref=db.backref('gastos', lazy=True))

    def __repr__(self):
        return f'<GastoTarjeta {self.concepto}>'

class Tarjeta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    banco = db.Column(db.String(100), nullable=False)
    es_adicional = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Tarjeta {self.nombre} - {self.banco}>'
    

@app.route('/')
@login_required
def index():
    #try:
        # Obtener datos de los últimos 30 días
        fecha_inicio = date.today() - timedelta(days=30)
        
        gastos = db.session.query(
            func.date(Gasto.fecha).label('fecha'),
            func.sum(Gasto.importe).label('total')
        ).filter(Gasto.fecha >= fecha_inicio).group_by(func.date(Gasto.fecha)).all()

        ingresos = db.session.query(
            func.date(Ingreso.fecha).label('fecha'),
            func.sum(Ingreso.importe).label('total')
        ).filter(Ingreso.fecha >= fecha_inicio).group_by(func.date(Ingreso.fecha)).all()

        total_gastos = db.session.query(func.sum(Gasto.importe)).scalar() or 0
        total_ingresos = db.session.query(func.sum(Ingreso.importe)).scalar() or 0

        # Preparar datos para el gráfico
        fechas = sorted(set([g.fecha for g in gastos] + [i.fecha for i in ingresos]))
        datos_gastos = {g.fecha: float(g.total) for g in gastos}
        datos_ingresos = {i.fecha: float(i.total) for i in ingresos}

        datos_grafico = [{
            'fecha': fecha, # .strftime('%Y-%m-%d'),
            'gastos': datos_gastos.get(fecha, 0),
            'ingresos': datos_ingresos.get(fecha, 0)
        } for fecha in fechas]

        # Obtener los últimos 5 gastos e ingresos
        ultimos_gastos = Gasto.query.order_by(Gasto.fecha.desc()).limit(5).all()
        ultimos_ingresos = Ingreso.query.order_by(Ingreso.fecha.desc()).limit(5).all()

        print(f"Número de gastos encontrados: {len(ultimos_gastos)}")
        for gasto in ultimos_gastos:
            print(f"Gasto: {gasto.concepto}, Fecha: {gasto.fecha}, Importe: {gasto.importe}")

        return render_template('index.html', 
                               total_gastos=total_gastos, 
                               total_ingresos=total_ingresos,
                               datos_grafico=datos_grafico,
                               ultimos_gastos=ultimos_gastos,
                               ultimos_ingresos=ultimos_ingresos)
        
    #except Exception as e:
    #    print(f"Error en la función index: {str(e)}")
    #    return render_template('error.html', error=str(e))

@app.route('/check_gastos')
@login_required
def check_gastos():
    todos_los_gastos = Gasto.query.all()
    return f"Número total de gastos: {len(todos_los_gastos)}"

@app.route('/gastos')
@login_required
def listar_gastos():
    gastos = Gasto.query.order_by(Gasto.fecha.desc()).all()
    return render_template('gastos/listar.html', gastos=gastos)

@app.route('/gastos/agregar', methods=['GET', 'POST'])
@login_required
def agregar_gasto():
    if request.method == 'POST':
        fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d').date()
        nuevo_gasto = Gasto(
            fecha=fecha,
            importe=float(request.form['importe']),
            concepto=request.form['concepto'],  # Actualizado
            categoria_id=int(request.form['categoria']),
            informacion_adicional=request.form.get('informacion_adicional')  # Nuevo campo
        )
        db.session.add(nuevo_gasto)
        db.session.commit()
        flash('Gasto agregado exitosamente', 'success')
        return redirect(url_for('listar_gastos'))
    categorias = Categoria.query.all()
    return render_template('gastos/agregar.html', categorias=categorias)

# CRUD para Categorías
@app.route('/categorias')
@login_required
def listar_categorias():
    categorias = Categoria.query.all()
    return render_template('categorias/listar.html', categorias=categorias)

@app.route('/categorias/agregar', methods=['GET', 'POST'])
@login_required
def agregar_categoria():
    if request.method == 'POST':
        nueva_categoria = Categoria(nombre=request.form['nombre'])
        db.session.add(nueva_categoria)
        db.session.commit()
        flash('Categoría agregada exitosamente', 'success')
        return redirect(url_for('listar_categorias'))
    return render_template('categorias/agregar.html')

@app.route('/categorias/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    if request.method == 'POST':
        categoria.nombre = request.form['nombre']
        db.session.commit()
        flash('Categoría actualizada exitosamente', 'success')
        return redirect(url_for('listar_categorias'))
    return render_template('categorias/editar_categorias.html', categoria=categoria)

@app.route('/categorias/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    db.session.delete(categoria)
    db.session.commit()
    flash('Categoría eliminada exitosamente', 'success')
    return redirect(url_for('listar_categorias'))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_gasto(id):
    gasto = Gasto.query.get_or_404(id)
    categorias = Categoria.query.all()
    if request.method == 'POST':
        gasto.importe = float(request.form['importe'])
        gasto.concepto = request.form['concepto']  # Actualizado
        gasto.categoria_id = int(request.form['categoria'])
        gasto.informacion_adicional = request.form.get('informacion_adicional')  # Nuevo campo
        db.session.commit()
        flash('Gasto actualizado exitosamente', 'success')
        return redirect(url_for('index'))
    return render_template('editar.html', gasto=gasto, categorias=categorias)

@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_gasto(id):
    gasto = Gasto.query.get_or_404(id)
    db.session.delete(gasto)
    db.session.commit()
    flash('Gasto eliminado exitosamente', 'success')
    return redirect(url_for('index'))

@app.route('/ingresos')
@login_required
def listar_ingresos():
    ingresos = Ingreso.query.filter_by(usuario_id=current_user.id).order_by(Ingreso.fecha.desc()).all()
    return render_template('ingresos/listar.html', ingresos=ingresos)

@app.route('/ingresos/agregar', methods=['GET', 'POST'])
@login_required
def agregar_ingreso():
    if request.method == 'POST':
        nuevo_ingreso = Ingreso(
            fecha=datetime.strptime(request.form['fecha'], '%Y-%m-%d').date(),
            importe=float(request.form['importe']),
            concepto=request.form['concepto'],
            detalle=request.form.get('detalle'),
            usuario_id=current_user.id
        )
        db.session.add(nuevo_ingreso)
        db.session.commit()
        flash('Ingreso agregado exitosamente', 'success')
        return redirect(url_for('listar_ingresos'))
    categorias = Categoria.query.all()
    return render_template('ingresos/agregar.html', categorias=categorias)

@app.route('/ingresos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_ingreso(id):
    ingreso = Ingreso.query.get_or_404(id)
    if request.method == 'POST':
        ingreso.importe = float(request.form['importe'])
        ingreso.concepto = request.form['concepto']
        ingreso.fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d').date()
        ingreso.detalle = request.form.get('detalle')
        db.session.commit()
        flash('Ingreso actualizado exitosamente', 'success')
        return redirect(url_for('listar_ingresos'))
    return render_template('ingresos/editar.html', ingreso=ingreso)

@app.route('/ingresos/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_ingreso(id):
    ingreso = Ingreso.query.get_or_404(id)
    db.session.delete(ingreso)
    db.session.commit()
    flash('Ingreso eliminado exitosamente', 'success')
    return redirect(url_for('listar_ingresos'))

@app.route('/gastos_tarjeta')
@login_required
def listar_gastos_tarjeta():
    gastos_tarjeta = GastoTarjeta.query.order_by(GastoTarjeta.fecha.desc()).all()
    return render_template('gastos_tarjeta/listar.html', gastos_tarjeta=gastos_tarjeta)

@app.route('/gastos_tarjeta/agregar', methods=['GET', 'POST'])
@login_required
def agregar_gasto_tarjeta():
    if request.method == 'POST':
        nuevo_gasto = GastoTarjeta(
            fecha=datetime.strptime(request.form['fecha'], '%Y-%m-%d').date(),
            concepto=request.form['concepto'],
            monto=float(request.form['monto']),
            cuota=request.form['cuota'],
            tarjeta_id=int(request.form['tarjeta'])
        )
        db.session.add(nuevo_gasto)
        db.session.commit()
        flash('Gasto con tarjeta agregado exitosamente', 'success')
        return redirect(url_for('listar_gastos_tarjeta'))
    tarjetas = Tarjeta.query.all()
    return render_template('gastos_tarjeta/agregar.html', tarjetas=tarjetas)

@app.route('/gastos_tarjeta/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_gasto_tarjeta(id):
    gasto = GastoTarjeta.query.get_or_404(id)
    if request.method == 'POST':
        gasto.fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d').date()
        gasto.concepto = request.form['concepto']
        gasto.monto = float(request.form['monto'])
        gasto.cuota = request.form['cuota']
        gasto.tarjeta_id = int(request.form['tarjeta'])
        db.session.commit()
        flash('Gasto con tarjeta actualizado exitosamente', 'success')
        return redirect(url_for('listar_gastos_tarjeta'))
    tarjetas = Tarjeta.query.all()
    return render_template('gastos_tarjeta/editar.html', gasto=gasto, tarjetas=tarjetas)

@app.route('/gastos_tarjeta/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_gasto_tarjeta(id):
    gasto = GastoTarjeta.query.get_or_404(id)
    db.session.delete(gasto)
    db.session.commit()
    flash('Gasto con tarjeta eliminado exitosamente', 'success')
    return redirect(url_for('listar_gastos_tarjeta'))

@app.route('/tarjetas', methods=['GET', 'POST'])
@login_required
def listar_tarjetas():
    tarjetas = Tarjeta.query.all()
    return render_template('tarjetas/listar.html', tarjetas=tarjetas)

@app.route('/tarjetas/agregar', methods=['GET', 'POST'])
@login_required
def agregar_tarjeta():
    if request.method == 'POST':
        tarjeta = Tarjeta(nombre=request.form['nombre'], banco=request.form['banco'], es_adicional=bool(request.form.get('es_adicional')))
        db.session.add(tarjeta)
        db.session.commit()
        flash('Tarjeta agregada exitosamente', 'success')
        return redirect(url_for('listar_tarjetas'))
    return render_template('tarjetas/agregar.html')

@app.route('/tarjetas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_tarjeta(id):
    tarjeta = Tarjeta.query.get_or_404(id)
    if request.method == 'POST':
        tarjeta.nombre = request.form['nombre']
        tarjeta.banco = request.form['banco']
        tarjeta.es_adicional = bool(request.form.get('es_adicional'))
        db.session.commit()
        flash('Tarjeta actualizada exitosamente', 'success')
        return redirect(url_for('listar_tarjetas'))
    return render_template('tarjetas/editar.html', tarjeta=tarjeta)

@app.route('/tarjetas/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_tarjeta(id):
    tarjeta = Tarjeta.query.get_or_404(id)
    db.session.delete(tarjeta)
    db.session.commit()
    flash('Tarjeta eliminada exitosamente', 'success')
    return redirect(url_for('listar_tarjetas'))

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/sw.js')
def service_worker():
    response = make_response(send_from_directory('static', 'sw.js'))
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Usuario.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('index'))
        flash('Usuario o contraseña incorrectos', 'error')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
        else:
            new_user = Usuario(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registro exitoso. Por favor, inicia sesión.', 'success')
            return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
