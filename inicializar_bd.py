"""
Script para crear la base de datos y poblarla con datos iniciales.
Ejecutar: venv\Scripts\python inicializar_bd.py
"""
from app import create_app, db
from app.models import (
    Departamento,
    FormaPago,
    Modulo,
    Municipio,
    Pais,
    Sexo,
    TipoIdentificacion,
    TipoUsuarioPaciente,
    Usuario,
)

app = create_app()

with app.app_context():
    print('Creando tablas en la base de datos...')
    db.create_all()
    print('Tablas creadas.')

    modulos_data = [
        ('admin', 'Administrador', 'bi-gear', '/admin', None, 1),
        ('pacientes', 'Pacientes', 'bi-person-heart', '/pacientes', None, 2),
        ('clientes', 'Clientes', 'bi-building', '/clientes', None, 3),
        ('cups', 'CUPS/Servicios', 'bi-clipboard2-pulse', '/cups', None, 4),
        ('atenciones', 'Atenciones', 'bi-clipboard-plus', '/atenciones', None, 5),
        ('cartera', 'Cartera', 'bi-receipt', '/cartera', None, 6),
        ('rips', 'RIPS', 'bi-filetype-json', '/rips', None, 7),
        ('informes', 'Informes', 'bi-graph-up', '/informes', None, 8),
        ('resultados', 'Resultados', 'bi-clipboard2-check', '/results', None, 9),
    ]

    for codigo, nombre, icono, url, _, orden in modulos_data:
        if not Modulo.query.filter_by(codigo=codigo).first():
            db.session.add(Modulo(codigo=codigo, nombre=nombre, icono=icono, url=url, orden=orden))
    db.session.commit()
    print('Modulos creados.')

    easy = Usuario.query.filter_by(username='EASY').first()
    if not easy:
        easy = Usuario(
            username='EASY',
            nombre='Administrador EASY',
            email='easy@laboratorio.local',
            rol='admin',
            activo=True,
        )
        easy.set_password('Easy2026*')
        db.session.add(easy)
        db.session.commit()
        print('Usuario EASY creado. Password: Easy2026*')
    else:
        print('Usuario EASY ya existe.')

    tipos_id = [
        ('CC', 'Cedula de Ciudadania'),
        ('TI', 'Tarjeta de Identidad'),
        ('RC', 'Registro Civil'),
        ('CE', 'Cedula de Extranjeria'),
        ('PA', 'Pasaporte'),
        ('MS', 'Menor sin identificacion'),
        ('AS', 'Adulto sin identificacion'),
        ('NIT', 'NIT'),
    ]
    for codigo, nombre in tipos_id:
        if not TipoIdentificacion.query.filter_by(codigo=codigo).first():
            db.session.add(TipoIdentificacion(codigo=codigo, nombre=nombre))
    db.session.commit()
    print('Tipos de identificacion creados.')

    tipos_usuario = [
        ('01', 'Contributivo'),
        ('02', 'Subsidiado'),
        ('03', 'Vinculado'),
        ('04', 'Particular'),
        ('05', 'Otro'),
    ]
    for codigo, nombre in tipos_usuario:
        if not TipoUsuarioPaciente.query.filter_by(codigo=codigo).first():
            db.session.add(TipoUsuarioPaciente(codigo=codigo, nombre=nombre))
    db.session.commit()
    print('Tipos de usuario paciente creados.')

    sexos = [('M', 'Masculino'), ('F', 'Femenino'), ('I', 'Indeterminado')]
    for codigo, nombre in sexos:
        if not Sexo.query.filter_by(codigo=codigo).first():
            db.session.add(Sexo(codigo=codigo, nombre=nombre))
    db.session.commit()
    print('Sexos creados.')

    formas_pago = [
        ('EFE', 'Efectivo'),
        ('TRAN', 'Transferencia Bancaria'),
        ('TAR', 'Tarjeta Credito/Debito'),
        ('CHE', 'Cheque'),
        ('CRED', 'Credito / Empresa'),
    ]
    for codigo, nombre in formas_pago:
        if not FormaPago.query.filter_by(codigo=codigo).first():
            db.session.add(FormaPago(codigo=codigo, nombre=nombre))
    db.session.commit()
    print('Formas de pago creadas.')

    colombia = Pais.query.filter_by(codigo='CO').first()
    if not colombia:
        colombia = Pais(codigo='CO', nombre='Colombia')
        db.session.add(colombia)
        db.session.commit()
        print('Pais Colombia creado.')

        departamentos = [
            ('11', 'Bogota D.C.'),
            ('05', 'Antioquia'),
            ('76', 'Valle del Cauca'),
            ('08', 'Atlantico'),
            ('17', 'Caldas'),
            ('63', 'Quindio'),
            ('66', 'Risaralda'),
            ('19', 'Cauca'),
            ('52', 'Narino'),
            ('54', 'Norte de Santander'),
            ('68', 'Santander'),
            ('25', 'Cundinamarca'),
            ('15', 'Boyaca'),
            ('73', 'Tolima'),
            ('41', 'Huila'),
        ]
        depto_objs = {}
        for codigo, nombre in departamentos:
            departamento = Departamento(codigo=codigo, nombre=nombre, pais_id=colombia.id)
            db.session.add(departamento)
            depto_objs[codigo] = departamento
        db.session.commit()

        bogota = depto_objs['11']
        localidades_bogota = [
            ('11001', 'Usaquen'),
            ('11002', 'Chapinero'),
            ('11003', 'Santa Fe'),
            ('11004', 'San Cristobal'),
            ('11005', 'Usme'),
            ('11006', 'Tunjuelito'),
            ('11007', 'Bosa'),
            ('11008', 'Kennedy'),
            ('11009', 'Fontibon'),
            ('11010', 'Engativa'),
            ('11011', 'Suba'),
            ('11012', 'Barrios Unidos'),
            ('11013', 'Teusaquillo'),
            ('11014', 'Martires'),
            ('11015', 'Antonio Narino'),
            ('11016', 'Puente Aranda'),
            ('11017', 'Candelaria'),
            ('11018', 'Rafael Uribe'),
            ('11019', 'Ciudad Bolivar'),
            ('11020', 'Sumapaz'),
        ]
        for codigo, nombre in localidades_bogota:
            db.session.add(
                Municipio(
                    codigo=codigo,
                    nombre=nombre,
                    departamento_id=bogota.id,
                    es_localidad=True,
                )
            )

        ciudades = [
            ('05001', '05', 'Medellin'),
            ('76001', '76', 'Cali'),
            ('08001', '08', 'Barranquilla'),
            ('17001', '17', 'Manizales'),
            ('63001', '63', 'Armenia'),
            ('66001', '66', 'Pereira'),
            ('54001', '54', 'Cucuta'),
            ('68001', '68', 'Bucaramanga'),
            ('52001', '52', 'Pasto'),
            ('41001', '41', 'Neiva'),
            ('73001', '73', 'Ibague'),
            ('15001', '15', 'Tunja'),
        ]
        for codigo, depto_codigo, nombre in ciudades:
            if depto_codigo in depto_objs:
                db.session.add(
                    Municipio(
                        codigo=codigo,
                        nombre=nombre,
                        departamento_id=depto_objs[depto_codigo].id,
                    )
                )
        db.session.commit()
        print('Departamentos y municipios de Colombia creados.')
    else:
        print('Datos de Colombia ya existen.')

    print('\nInicializacion completada.')
    print('URL: http://127.0.0.1:5000')
    print('Usuario: EASY')
    print('Password: Easy2026*')
