from app import app, db
from app.models import Gasto, Ingreso, GastoTarjeta  # Importa los modelos que necesites
import csv
from datetime import datetime

# Asegúrate de que la aplicación esté en el contexto correcto
app.app_context().push()

def importar_gastos(archivo_csv):
    with open(archivo_csv, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            gasto = Gasto(
                fecha=datetime.strptime(row['fecha'], '%Y-%m-%d').date(),
                importe=float(row['importe']),
                concepto=row['concepto'],
                categoria_id=int(row['categoria_id']),
                detalle=row.get('detalle', '')
            )
            db.session.add(gasto)
    db.session.commit()

def importar_ingresos(archivo_csv):
    with open(archivo_csv, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            ingreso = Ingreso(
                fecha=datetime.strptime(row['fecha'], '%Y-%m-%d').date(),
                importe=float(row['importe']),
                concepto=row['concepto'],
                detalle=row.get('detalle', '')
            )
            db.session.add(ingreso)
    db.session.commit()

def importar_gastos_tarjeta(archivo_csv):
    with open(archivo_csv, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            gasto_tarjeta = GastoTarjeta(
                fecha=datetime.strptime(row['fecha'], '%Y-%m-%d').date(),
                concepto=row['concepto'],
                monto=float(row['monto']),
                cuota=row['cuota']
            )
            db.session.add(gasto_tarjeta)
    db.session.commit()

if __name__ == '__main__':
    importar_gastos('datos/Egresos2024.csv')
    importar_ingresos('datos/Ingresos2024.csv')
    importar_gastos_tarjeta('datos/gastos_tarjeta.csv')
    print("Importación completada")

### Formato de importación
#fecha,importe,concepto,categoria_id,detalle
#2023-05-01,100.50,Compra de alimentos,1,Supermercado local
#2023-05-02,50.00,Transporte,2,Taxi al trabajo