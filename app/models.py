"""
Modelos de base de datos - Laboratorio Clínico
"""
import json
import uuid
from datetime import date, datetime, time
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


# =============================================================================
# TABLAS DE APOYO / CATÁLOGOS
# =============================================================================

class Pais(db.Model):
    __tablename__ = 'paises'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(5), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.Boolean, default=True)

    departamentos = db.relationship('Departamento', backref='pais', lazy='dynamic')

    def __repr__(self):
        return f'<Pais {self.nombre}>'


class Departamento(db.Model):
    __tablename__ = 'departamentos'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    pais_id = db.Column(db.Integer, db.ForeignKey('paises.id'), nullable=False)
    estado = db.Column(db.Boolean, default=True)

    municipios = db.relationship('Municipio', backref='departamento', lazy='dynamic')

    def __repr__(self):
        return f'<Departamento {self.nombre}>'


class Municipio(db.Model):
    __tablename__ = 'municipios'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    departamento_id = db.Column(db.Integer, db.ForeignKey('departamentos.id'), nullable=False)
    es_localidad = db.Column(db.Boolean, default=False)  # True para localidades de Bogotá
    estado = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Municipio {self.nombre}>'


class TipoIdentificacion(db.Model):
    __tablename__ = 'tipos_identificacion'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(5), unique=True, nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<TipoId {self.codigo}>'


class TipoUsuarioPaciente(db.Model):
    """Tipo de usuario del paciente (contributivo, subsidiado, particular, etc.)"""
    __tablename__ = 'tipos_usuario_paciente'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(5), unique=True, nullable=False)
    nombre = db.Column(db.String(80), nullable=False)
    estado = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<TipoUsuario {self.nombre}>'


class Sexo(db.Model):
    __tablename__ = 'sexos'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(2), unique=True, nullable=False)
    nombre = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<Sexo {self.nombre}>'


class FormaPago(db.Model):
    __tablename__ = 'formas_pago'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(5), unique=True, nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<FormaPago {self.nombre}>'


# =============================================================================
# USUARIOS DEL SISTEMA
# =============================================================================

class Modulo(db.Model):
    """Módulos/opciones del sistema para control de permisos"""
    __tablename__ = 'modulos'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    icono = db.Column(db.String(50))
    url = db.Column(db.String(200))
    padre_id = db.Column(db.Integer, db.ForeignKey('modulos.id'), nullable=True)
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)

    hijos = db.relationship('Modulo', backref=db.backref('padre', remote_side=[id]),
                            lazy='dynamic')

    def __repr__(self):
        return f'<Modulo {self.nombre}>'


# Tabla asociativa usuario-modulos (permisos)
usuario_modulos = db.Table('usuario_modulos',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('modulo_id', db.Integer, db.ForeignKey('modulos.id'), primary_key=True)
)


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(20), default='operador')  # admin, supervisor, operador
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acceso = db.Column(db.DateTime)

    modulos = db.relationship('Modulo', secondary=usuario_modulos, lazy='subquery',
                              backref=db.backref('usuarios', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def tiene_permiso(self, codigo_modulo):
        if self.rol == 'admin':
            return True
        return any(m.codigo == codigo_modulo for m in self.modulos)

    def get_menu(self):
        """Retorna los módulos raíz accesibles por el usuario"""
        if self.rol == 'admin':
            return Modulo.query.filter_by(padre_id=None, activo=True).order_by(Modulo.orden).all()
        return [m for m in self.modulos if m.padre_id is None and m.activo]

    def __repr__(self):
        return f'<Usuario {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# =============================================================================
# PACIENTES
# =============================================================================

class Paciente(db.Model):
    __tablename__ = 'pacientes'
    # Identificación es la llave única (no autoincremental)
    identificacion = db.Column(db.String(20), primary_key=True)
    tipo_id_id = db.Column(db.Integer, db.ForeignKey('tipos_identificacion.id'), nullable=False)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    sexo_id = db.Column(db.Integer, db.ForeignKey('sexos.id'), nullable=False)
    tipo_usuario_id = db.Column(db.Integer, db.ForeignKey('tipos_usuario_paciente.id'))
    pais_nacimiento_id = db.Column(db.Integer, db.ForeignKey('paises.id'))
    pais_residencia_id = db.Column(db.Integer, db.ForeignKey('paises.id'))
    departamento_id = db.Column(db.Integer, db.ForeignKey('departamentos.id'))
    municipio_id = db.Column(db.Integer, db.ForeignKey('municipios.id'))
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(20))
    celular = db.Column(db.String(20))
    email = db.Column(db.String(120))
    estado = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_crea_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    # Relaciones
    tipo_id = db.relationship('TipoIdentificacion', foreign_keys=[tipo_id_id])
    sexo = db.relationship('Sexo', foreign_keys=[sexo_id])
    tipo_usuario = db.relationship('TipoUsuarioPaciente', foreign_keys=[tipo_usuario_id])
    pais_nacimiento = db.relationship('Pais', foreign_keys=[pais_nacimiento_id])
    pais_residencia = db.relationship('Pais', foreign_keys=[pais_residencia_id])
    departamento = db.relationship('Departamento', foreign_keys=[departamento_id])
    municipio = db.relationship('Municipio', foreign_keys=[municipio_id])
    usuario_crea = db.relationship('Usuario', foreign_keys=[usuario_crea_id])

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'

    def __repr__(self):
        return f'<Paciente {self.identificacion} - {self.nombre_completo}>'


# =============================================================================
# CLIENTES / EMPRESAS
# =============================================================================

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    tipo_identificacion = db.Column(db.String(5))  # NIT, CC
    nro_identificacion = db.Column(db.String(20))
    pais_id = db.Column(db.Integer, db.ForeignKey('paises.id'))
    municipio_id = db.Column(db.Integer, db.ForeignKey('municipios.id'))
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(120))
    # Contacto facturación
    contacto_facturacion = db.Column(db.String(100))
    dir_facturacion = db.Column(db.String(200))
    tel_facturacion = db.Column(db.String(20))
    email_facturacion = db.Column(db.String(120))
    # Contacto administrativo
    contacto_administrativo = db.Column(db.String(100))
    dir_administrativo = db.Column(db.String(200))
    tel_administrativo = db.Column(db.String(20))
    email_administrativo = db.Column(db.String(120))
    # Financiero
    lista_precio_id = db.Column(db.Integer, db.ForeignKey('listas_precios.id'), nullable=True)
    codigo_tarifa = db.Column(db.String(50))  # referencia histórica / nombre hoja Excel
    tipo_usuario_rips = db.Column(db.String(5), default='12')  # Tipo usuario para RIPS (11, 12, etc.)
    porcentaje_iva = db.Column(db.Numeric(5, 2), default=0)
    porcentaje_retfte = db.Column(db.Numeric(5, 2), default=0)
    estado = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_crea_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    # Relaciones
    pais = db.relationship('Pais', foreign_keys=[pais_id])
    municipio = db.relationship('Municipio', foreign_keys=[municipio_id])
    usuario_crea = db.relationship('Usuario', foreign_keys=[usuario_crea_id])
    tarifas = db.relationship('TarifaCliente', backref='cliente', lazy='dynamic',
                              cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Cliente {self.codigo} - {self.nombre}>'


# =============================================================================
# PERSONAS QUE ATIENDEN (bacteriólogas, auxiliares, etc.)
# =============================================================================

class PersonaAtiende(db.Model):
    """Personal del laboratorio que toma las muestras / atiende pacientes"""
    __tablename__ = 'personas_atienden'
    id = db.Column(db.Integer, primary_key=True)
    tipo_identificacion = db.Column(db.String(5), default='CC')
    identificacion = db.Column(db.String(20), unique=True, nullable=False)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(80))  # Bacterióloga, Auxiliar, etc.
    celular = db.Column(db.String(20))
    estado = db.Column(db.Boolean, default=True)

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'

    def __repr__(self):
        return f'<PersonaAtiende {self.identificacion} - {self.nombre_completo}>'


# =============================================================================
# LISTAS DE PRECIOS (tablas de tarifas reutilizables)
# =============================================================================

class ListaPrecio(db.Model):
    """Una lista de precios es un conjunto de CUPS con sus valores.
    Una lista puede ser asignada a uno o más clientes."""
    __tablename__ = 'listas_precios'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(200))
    estado = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('ListaPrecioItem', backref='lista', lazy='dynamic',
                            cascade='all, delete-orphan')
    clientes = db.relationship('Cliente', backref='lista_precio', lazy='dynamic')

    def __repr__(self):
        return f'<ListaPrecio {self.codigo}>'


class ListaPrecioItem(db.Model):
    """Ítem individual de una lista de precios: CUPS + valor."""
    __tablename__ = 'listas_precios_items'
    id = db.Column(db.Integer, primary_key=True)
    lista_id = db.Column(db.Integer, db.ForeignKey('listas_precios.id'), nullable=False)
    cups_codigo = db.Column(db.String(10), db.ForeignKey('cups.codigo'), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)

    cups = db.relationship('Cups', foreign_keys=[cups_codigo])

    __table_args__ = (
        db.UniqueConstraint('lista_id', 'cups_codigo', name='uq_lista_cups'),
    )

    def __repr__(self):
        return f'<ListaItem {self.lista_id}-{self.cups_codigo}>'




class Cups(db.Model):
    __tablename__ = 'cups'
    codigo = db.Column(db.String(10), primary_key=True)
    descripcion = db.Column(db.String(300), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    es_transporte = db.Column(db.Boolean, default=False)
    estado = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<CUPS {self.codigo}>'


class TarifaCliente(db.Model):
    """Lista de precios / tarifa asignada a cada cliente"""
    __tablename__ = 'tarifas_clientes'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    cups_codigo = db.Column(db.String(10), db.ForeignKey('cups.codigo'), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)

    cups = db.relationship('Cups', foreign_keys=[cups_codigo])

    __table_args__ = (
        db.UniqueConstraint('cliente_id', 'cups_codigo', name='uq_tarifa_cliente_cups'),
    )

    def __repr__(self):
        return f'<Tarifa {self.cliente_id}-{self.cups_codigo}>'


# =============================================================================
# NUMERACIÓN / CONSECUTIVOS
# =============================================================================

class NumeracionInicial(db.Model):
    """Numeración inicial de consecutivos, prefacturas y recibos de caja por año"""
    __tablename__ = 'numeracion_inicial'
    id = db.Column(db.Integer, primary_key=True)
    anio = db.Column(db.Integer, nullable=False)
    prefijo_atencion = db.Column(db.String(10), default='')
    consecutivo_atencion = db.Column(db.Integer, default=1)
    prefijo_prefactura = db.Column(db.String(10), default='PF')
    consecutivo_prefactura = db.Column(db.Integer, default=1)
    prefijo_recibo = db.Column(db.String(10), default='RC')
    consecutivo_recibo = db.Column(db.Integer, default=1)

    __table_args__ = (
        db.UniqueConstraint('anio', name='uq_numeracion_anio'),
    )

    def __repr__(self):
        return f'<Numeracion {self.anio}>'


# =============================================================================
# ATENCIONES
# =============================================================================

class AtencionEncabezado(db.Model):
    __tablename__ = 'atenciones_encabezado'
    nro_consecutivo = db.Column(db.String(20), primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    paciente_id = db.Column(db.String(20), db.ForeignKey('pacientes.identificacion'), nullable=False)
    fecha_atencion = db.Column(db.Date, nullable=False)
    autorizacion = db.Column(db.String(50))
    autorizacion_transporte = db.Column(db.String(50))
    persona_atiende_id = db.Column(db.Integer, db.ForeignKey('personas_atienden.id'), nullable=True)
    forma_pago_id = db.Column(db.Integer, db.ForeignKey('formas_pago.id'))
    abono_cliente = db.Column(db.Numeric(12, 2), default=0)
    forma_abono_id = db.Column(db.Integer, db.ForeignKey('formas_pago.id'))
    saldo_empresa = db.Column(db.Numeric(12, 2), default=0)
    # Estado: Ingresado, Prefacturado, Cancelado, Anulado
    estado = db.Column(db.String(20), default='Ingresado')
    fecha_hora_ingreso = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_ingresa_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    # Relaciones
    cliente = db.relationship('Cliente', foreign_keys=[cliente_id])
    paciente = db.relationship('Paciente', foreign_keys=[paciente_id])
    persona_atiende = db.relationship('PersonaAtiende', foreign_keys=[persona_atiende_id])
    forma_pago = db.relationship('FormaPago', foreign_keys=[forma_pago_id])
    forma_abono = db.relationship('FormaPago', foreign_keys=[forma_abono_id])
    usuario_ingresa = db.relationship('Usuario', foreign_keys=[usuario_ingresa_id])
    detalles = db.relationship('AtencionDetalle', backref='atencion', lazy='dynamic',
                               cascade='all, delete-orphan')

    @property
    def valor_total(self):
        return sum(d.valor for d in self.detalles)

    def __repr__(self):
        return f'<Atencion {self.nro_consecutivo}>'


class AtencionDetalle(db.Model):
    __tablename__ = 'atenciones_detalle'
    id = db.Column(db.Integer, primary_key=True)
    nro_consecutivo = db.Column(db.String(20), db.ForeignKey('atenciones_encabezado.nro_consecutivo'),
                                nullable=False)
    secuencia = db.Column(db.Integer, nullable=False)
    cups_codigo = db.Column(db.String(10), db.ForeignKey('cups.codigo'), nullable=False)
    valor = db.Column(db.Numeric(12, 2), nullable=False)

    cups = db.relationship('Cups', foreign_keys=[cups_codigo])

    __table_args__ = (
        db.UniqueConstraint('nro_consecutivo', 'secuencia', name='uq_detalle_consec_seq'),
    )

    def __repr__(self):
        return f'<Detalle {self.nro_consecutivo}-{self.secuencia}>'


# =============================================================================
# PREFACTURAS Y CARTERA
# =============================================================================

class Prefactura(db.Model):
    __tablename__ = 'prefacturas'
    id = db.Column(db.Integer, primary_key=True)
    nro_prefactura = db.Column(db.String(20), unique=True, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    fecha_generacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_desde = db.Column(db.Date)
    fecha_hasta = db.Column(db.Date)
    valor_total = db.Column(db.Numeric(14, 2), default=0)
    estado = db.Column(db.String(20), default='Pendiente')  # Pendiente, Pagada, Parcial
    usuario_genera_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    cliente = db.relationship('Cliente', foreign_keys=[cliente_id])
    usuario_genera = db.relationship('Usuario', foreign_keys=[usuario_genera_id])
    atenciones = db.relationship('PrefacturaDetalle', backref='prefactura', lazy='dynamic',
                                 cascade='all, delete-orphan')
    recibos = db.relationship('ReciboCaja', backref='prefactura', lazy='dynamic')

    def __repr__(self):
        return f'<Prefactura {self.nro_prefactura}>'


class PrefacturaDetalle(db.Model):
    """Atenciones incluidas en cada prefactura"""
    __tablename__ = 'prefacturas_detalle'
    id = db.Column(db.Integer, primary_key=True)
    prefactura_id = db.Column(db.Integer, db.ForeignKey('prefacturas.id'), nullable=False)
    nro_consecutivo = db.Column(db.String(20), db.ForeignKey('atenciones_encabezado.nro_consecutivo'),
                                nullable=False)

    atencion = db.relationship('AtencionEncabezado', foreign_keys=[nro_consecutivo])


class ReciboCaja(db.Model):
    __tablename__ = 'recibos_caja'
    id = db.Column(db.Integer, primary_key=True)
    nro_recibo = db.Column(db.String(20), unique=True, nullable=False)
    prefactura_id = db.Column(db.Integer, db.ForeignKey('prefacturas.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    fecha_pago = db.Column(db.DateTime, default=datetime.utcnow)
    valor_pagado = db.Column(db.Numeric(14, 2), nullable=False)
    forma_pago_id = db.Column(db.Integer, db.ForeignKey('formas_pago.id'))
    observaciones = db.Column(db.String(300))
    usuario_registra_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    cliente = db.relationship('Cliente', foreign_keys=[cliente_id])
    forma_pago = db.relationship('FormaPago', foreign_keys=[forma_pago_id])
    usuario_registra = db.relationship('Usuario', foreign_keys=[usuario_registra_id])

    def __repr__(self):
        return f'<Recibo {self.nro_recibo}>'


# =============================================================================
# CONFIGURACIÓN RIPS
# =============================================================================

class ConfigRips(db.Model):
    """Datos del facturador y configuración RIPS"""
    __tablename__ = 'config_rips'
    id = db.Column(db.Integer, primary_key=True)
    nit_facturador = db.Column(db.String(20))
    razon_social = db.Column(db.String(150))
    codigo_habilitacion = db.Column(db.String(20))
    cups_transporte = db.Column(db.String(10), db.ForeignKey('cups.codigo'))
    tipo_usuario_rips = db.Column(db.String(5))
    modalidad_atencion = db.Column(db.String(5))
    ambito_atencion = db.Column(db.String(5))
    # Campos fijos de procedimientos
    via_ingreso = db.Column(db.String(5), default='02')
    grupo_servicios = db.Column(db.String(5), default='02')
    cod_servicio = db.Column(db.String(10), default='739')
    finalidad_tecnologia = db.Column(db.String(5), default='15')
    concepto_recaudo = db.Column(db.String(5), default='05')
    zona_territorial = db.Column(db.String(5), default='02')
    tipo_doc_prestador = db.Column(db.String(5), default='CC')
    num_doc_prestador = db.Column(db.String(20))
    cod_diagnostico_principal = db.Column(db.String(10), default='Z000')

    cups_transporte_rel = db.relationship('Cups', foreign_keys=[cups_transporte])

    def __repr__(self):
        return f'<ConfigRips {self.nit_facturador}>'


# =============================================================================
# MODULO DE RESULTADOS
# =============================================================================

class UserResultProfile(db.Model):
    __tablename__ = 'user_result_profiles'

    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), primary_key=True)
    role = db.Column(db.String(20), nullable=False, default='bacteriologist')
    professional_id = db.Column(db.String(50))
    signature_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('Usuario', backref=db.backref('results_profile', uselist=False, cascade='all, delete-orphan'))


class Exam(db.Model):
    __tablename__ = 'exams'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    integration_code = db.Column(db.String(50), index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='human')
    description = db.Column(db.Text)
    technique = db.Column(db.String(300))
    equipment = db.Column(db.String(300))
    method = db.Column(db.String(300))
    sample_type = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def matches_requested_code(self, requested_code):
        normalized = (requested_code or '').strip().upper()
        aliases = {self.code.upper()}
        if self.integration_code:
            aliases.add(self.integration_code.upper())
        return normalized in aliases

    def __repr__(self):
        return f'<Exam {self.code} - {self.name}>'


class Parameter(db.Model):
    __tablename__ = 'parameters'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    result_type = db.Column(db.String(20), nullable=False, default='decimal')
    default_units = db.Column(db.String(50))
    is_fixed = db.Column(db.Boolean, default=False)
    fixed_value = db.Column(db.String(200))
    order_index = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)

    exam = db.relationship('Exam', backref=db.backref('parameters', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Parameter {self.name} ({self.exam_id})>'


class ReferenceValue(db.Model):
    __tablename__ = 'reference_values'

    id = db.Column(db.Integer, primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.id'), nullable=False)
    gender = db.Column(db.String(10))
    min_age = db.Column(db.Integer)
    max_age = db.Column(db.Integer)
    ref_type = db.Column(db.String(10), nullable=False, default='range')
    min_value = db.Column(db.Float)
    max_value = db.Column(db.Float)
    exact_value = db.Column(db.Float)
    text_value = db.Column(db.String(300))
    units = db.Column(db.String(50))

    parameter = db.relationship('Parameter', backref=db.backref('reference_values', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<ReferenceValue param={self.parameter_id}>'


class LayoutCell(db.Model):
    __tablename__ = 'layout_cells'

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    row = db.Column(db.Integer, nullable=False)
    col = db.Column(db.Integer, nullable=False)
    rowspan = db.Column(db.Integer, default=1)
    colspan = db.Column(db.Integer, default=1)
    cell_type = db.Column(db.String(20), default='label')
    content = db.Column(db.Text)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.id'))
    style = db.Column(db.Text)

    exam = db.relationship('Exam', backref=db.backref('layout_cells', lazy='dynamic', cascade='all, delete-orphan'))
    parameter = db.relationship('Parameter')

    @property
    def style_dict(self):
        if not self.style:
            return {}
        try:
            return json.loads(self.style)
        except Exception:
            return {}

    def __repr__(self):
        return f'<LayoutCell exam={self.exam_id} r={self.row} c={self.col}>'


class Result(db.Model):
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), db.ForeignKey('atenciones_encabezado.nro_consecutivo'), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    bacteriologist_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='draft')
    qr_token = db.Column(db.String(100), unique=True, index=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = db.relationship('AtencionEncabezado', backref=db.backref('results', lazy='dynamic'))
    exam = db.relationship('Exam', backref=db.backref('results', lazy='dynamic'))
    bacteriologist = db.relationship('Usuario', foreign_keys=[bacteriologist_id], backref=db.backref('results_as_bacteriologist', lazy='dynamic'))
    reviewer = db.relationship('Usuario', foreign_keys=[reviewer_id], backref=db.backref('results_as_reviewer', lazy='dynamic'))

    def generate_qr_token(self):
        self.qr_token = str(uuid.uuid4()).replace('-', '')

    @property
    def has_alarms(self):
        return any(parameter_result.out_of_range for parameter_result in self.parameter_results)

    def __repr__(self):
        return f'<Result order={self.order_id} exam={self.exam_id}>'


class ParameterResult(db.Model):
    __tablename__ = 'parameter_results'

    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('results.id'), nullable=False)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.id'), nullable=False)
    value = db.Column(db.Text)
    units = db.Column(db.String(50))
    out_of_range = db.Column(db.Boolean, default=False)
    flagged = db.Column(db.Boolean, default=False)

    result = db.relationship('Result', backref=db.backref('parameter_results', lazy='dynamic', cascade='all, delete-orphan'))
    parameter = db.relationship('Parameter', backref=db.backref('parameter_results', lazy='dynamic'))

    def __repr__(self):
        return f'<ParameterResult result={self.result_id} param={self.parameter_id}>'


class PDFConfig(db.Model):
    __tablename__ = 'pdf_configs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    name = db.Column(db.String(100), nullable=False, default='Default')
    is_default = db.Column(db.Boolean, default=False)
    logo_path = db.Column(db.String(500))
    logo_position = db.Column(db.String(20), default='header')
    logo_alignment = db.Column(db.String(20), default='left')
    page_number_style = db.Column(db.String(20), default='none')
    header_text = db.Column(db.Text)
    footer_text = db.Column(db.Text)
    patient_info_layout = db.Column(db.Text)
    institution_name = db.Column(db.String(200))
    institution_address = db.Column(db.String(400))
    institution_phone = db.Column(db.String(100))
    page_size = db.Column(db.String(20), default='A4')
    margin_top = db.Column(db.Float, default=20.0)
    margin_bottom = db.Column(db.Float, default=20.0)
    margin_left = db.Column(db.Float, default=20.0)
    margin_right = db.Column(db.Float, default=20.0)
    show_qr = db.Column(db.Boolean, default=True)
    show_watermark = db.Column(db.Boolean, default=False)
    watermark_text = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('Usuario', backref=db.backref('pdf_configs', lazy='dynamic'))

    def __repr__(self):
        return f'<PDFConfig {self.name}>'


@property
def _usuario_name(self):
    return self.nombre


@property
def _usuario_role(self):
    if self.rol == 'admin':
        return 'admin'
    if self.results_profile and self.results_profile.role:
        return self.results_profile.role
    return 'operator'


@_usuario_role.setter
def _usuario_role(self, value):
    role_value = (value or '').strip() or 'bacteriologist'
    if not self.results_profile:
        self.results_profile = UserResultProfile()
    self.results_profile.role = role_value
    if role_value == 'admin':
        self.rol = 'admin'
    elif self.rol == 'admin':
        self.rol = 'operador'


@property
def _usuario_professional_id(self):
    return self.results_profile.professional_id if self.results_profile else None


@_usuario_professional_id.setter
def _usuario_professional_id(self, value):
    if not self.results_profile:
        self.results_profile = UserResultProfile()
    self.results_profile.professional_id = (value or '').strip() or None


@property
def _usuario_signature_image(self):
    return self.results_profile.signature_image if self.results_profile else None


@_usuario_signature_image.setter
def _usuario_signature_image(self, value):
    if not self.results_profile:
        self.results_profile = UserResultProfile()
    self.results_profile.signature_image = (value or '').strip() or None


@property
def _usuario_active(self):
    return self.activo


@_usuario_active.setter
def _usuario_active(self, value):
    self.activo = bool(value)


@property
def _paciente_id(self):
    return self.identificacion


@property
def _paciente_name(self):
    return self.nombre_completo


@property
def _paciente_birth_date(self):
    return self.fecha_nacimiento


@property
def _paciente_gender(self):
    return self.sexo.codigo if self.sexo else None


@property
def _paciente_document_type(self):
    return self.tipo_id.codigo if self.tipo_id else ''


@property
def _paciente_phone(self):
    return self.celular or self.telefono


@property
def _paciente_address(self):
    return self.direccion


@property
def _paciente_age(self):
    if not self.fecha_nacimiento:
        return None
    return (date.today() - self.fecha_nacimiento).days // 365


@property
def _atencion_id(self):
    return self.nro_consecutivo


@property
def _atencion_consecutive(self):
    return self.nro_consecutivo


@property
def _atencion_patient(self):
    return self.paciente


@property
def _atencion_requested_exams(self):
    return self.detalles


@property
def _atencion_date(self):
    if self.fecha_hora_ingreso:
        return self.fecha_hora_ingreso
    if self.fecha_atencion:
        return datetime.combine(self.fecha_atencion, time.min)
    return datetime.utcnow()


@property
def _atencion_attending_physician(self):
    return self.persona_atiende.nombre_completo if self.persona_atiende else ''


@property
def _atencion_diagnosis(self):
    return self.autorizacion or ''


@property
def _atencion_notes(self):
    return self.autorizacion_transporte or ''


Usuario.name = _usuario_name
Usuario.role = _usuario_role
Usuario.professional_id = _usuario_professional_id
Usuario.signature_image = _usuario_signature_image
Usuario.active = _usuario_active
Paciente.id = _paciente_id
Paciente.name = _paciente_name
Paciente.birth_date = _paciente_birth_date
Paciente.gender = _paciente_gender
Paciente.document_type = _paciente_document_type
Paciente.phone = _paciente_phone
Paciente.address = _paciente_address
Paciente.age = _paciente_age
Paciente.document = Paciente.identificacion
AtencionEncabezado.id = _atencion_id
AtencionEncabezado.consecutive = AtencionEncabezado.nro_consecutivo
AtencionEncabezado.patient_id = AtencionEncabezado.paciente_id
AtencionEncabezado.patient = _atencion_patient
AtencionEncabezado.requested_exams = _atencion_requested_exams
AtencionEncabezado.date = _atencion_date
AtencionEncabezado.attending_physician = _atencion_attending_physician
AtencionEncabezado.diagnosis = _atencion_diagnosis
AtencionEncabezado.notes = _atencion_notes
AtencionDetalle.order_id = AtencionDetalle.nro_consecutivo
AtencionDetalle.sequence = AtencionDetalle.secuencia
AtencionDetalle.requested_code = AtencionDetalle.cups_codigo
AtencionDetalle.value = AtencionDetalle.valor

User = Usuario
Patient = Paciente
Order = AtencionEncabezado
OrderExam = AtencionDetalle
