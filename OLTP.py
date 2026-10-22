import pandas as pd
import numpy as np
from sqlalchemy import create_engine

# ==========================================
# 1. SIMULACIÓN DE INGESTA OPERATIVA (OLTP)
# ==========================================
np.random.seed(101)
n = 500

df_operativo = pd.DataFrame({
    'id_transaccion': range(1000, 1000 + n),
    'fecha_hora': pd.date_range(start='2026-01-01', periods=n, freq='h'),
    'cliente_nombre': np.random.choice(['Juan Pérez', 'María Gómez', 'Carlos Ruiz'], n),
    'cliente_ciudad': np.random.choice(['Puebla', 'CDMX', 'Guadalajara'], n),
    'producto_nombre': np.random.choice(['Laptop Dell', 'Mouse Logi', 'Monitor LG'], n),
    'categoria_prod': np.random.choice(['Cómputo', 'Accesorios', 'Pantallas'], n),
    'precio_unitario': np.random.choice([15000.0, 350.0, 4500.0], n),
    'cantidad': np.random.randint(1, 5, n)
})

# ==========================================
# 2. CONSTRUCCIÓN DE DIMENSIONES Y HECHOS
# ==========================================

# Dimensión Cliente
dim_cliente = df_operativo[['cliente_nombre', 'cliente_ciudad']].drop_duplicates().reset_index(drop=True)
dim_cliente['id_cliente_sk'] = dim_cliente.index + 1

# Dimensión Producto
dim_producto = df_operativo[['producto_nombre', 'categoria_prod', 'precio_unitario']].drop_duplicates().reset_index(drop=True)
dim_producto['id_producto_sk'] = dim_producto.index + 1

# Dimensión Tiempo (Con atributos extendidos solicitados: día de la semana y fin de semana)
dim_tiempo = pd.DataFrame({'fecha_completa': df_operativo['fecha_hora'].dt.date.unique()})
dim_tiempo['fecha_completa'] = pd.to_datetime(dim_tiempo['fecha_completa'])
dim_tiempo['id_tiempo_sk'] = dim_tiempo['fecha_completa'].dt.strftime('%Y%m%d').astype(int)
dim_tiempo['anio'] = dim_tiempo['fecha_completa'].dt.year
dim_tiempo['mes'] = dim_tiempo['fecha_completa'].dt.month
dim_tiempo['dia'] = dim_tiempo['fecha_completa'].dt.day
dim_tiempo['dia_semana'] = dim_tiempo['fecha_completa'].dt.day_name()
dim_tiempo['es_fin_semana'] = dim_tiempo['fecha_completa'].dt.weekday >= 5

# Tabla de Hechos (Fact_Ventas)
fact_ventas = df_operativo.merge(dim_cliente, on=['cliente_nombre', 'cliente_ciudad']) \
                          .merge(dim_producto, on=['producto_nombre', 'categoria_prod', 'precio_unitario'])

fact_ventas['fecha_completa'] = pd.to_datetime(fact_ventas['fecha_hora'].dt.date)
fact_ventas = fact_ventas.merge(dim_tiempo, on='fecha_completa')

# Métricas calculadas adicionales (Subtotal, Impuesto/IVA 16%, y Monto Total Final)
fact_ventas['subtotal'] = fact_ventas['cantidad'] * fact_ventas['precio_unitario']
fact_ventas['impuesto'] = fact_ventas['subtotal'] * 0.16
fact_ventas['monto_total'] = fact_ventas['subtotal'] + fact_ventas['impuesto']

# Selección final de columnas para la Fact Table
fact_table = fact_ventas[[
    'id_transaccion', 'id_cliente_sk', 'id_producto_sk', 'id_tiempo_sk', 
    'cantidad', 'subtotal', 'impuesto', 'monto_total'
]]

print("=== TABLA DE HECHOS (FACT_VENTAS) ===")
print(fact_table.head())

# ==========================================
# 3. CARGA A POSTGRESQL EN AWS EC2 (Opcional/Desafío)
# ==========================================
# Reemplaza con tus credenciales reales de la instancia EC2
DB_USER = "postgres"
DB_PASSWORD = "use123ab"  # Cambia esto por tu contraseña real
DB_HOST = "localhost"               # Cambiado a localhost porque estás dentro de la EC2
DB_PORT = "5432"
DB_NAME = "warehouse_db"

engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

dim_cliente.to_sql('dim_cliente', engine, if_exists='replace', index=False)
dim_producto.to_sql('dim_producto', engine, if_exists='replace', index=False)
dim_tiempo.to_sql('dim_tiempo', engine, if_exists='replace', index=False)
fact_table.to_sql('fact_ventas', engine, if_exists='replace', index=False)
print("¡Datos cargados exitosamente en PostgreSQL (EC2)!")