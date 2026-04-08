"""
Script para consultar la base de datos de empleos SERVIR
"""
import sqlite3

DATABASE_FILE = "empleos_servir.db"

def consultar():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("📊 ESTADÍSTICAS DE LA BASE DE DATOS")
    print("="*60)
    
    # Total de ofertas
    cursor.execute("SELECT COUNT(*) FROM ofertas")
    total = cursor.fetchone()[0]
    print(f"\n📦 Total de ofertas: {total}")
    
    # Ofertas activas
    cursor.execute("SELECT COUNT(*) FROM ofertas WHERE activo = 1")
    activas = cursor.fetchone()[0]
    print(f"✅ Ofertas activas: {activas}")
    
    # Remuneración promedio
    cursor.execute("SELECT AVG(remuneracion) FROM ofertas WHERE remuneracion > 0")
    promedio = cursor.fetchone()[0]
    if promedio:
        print(f"💰 Remuneración promedio: S/{promedio:,.0f}")
    
    # Remuneración máxima
    cursor.execute("SELECT MAX(remuneracion) FROM ofertas")
    maxima = cursor.fetchone()[0]
    if maxima:
        print(f"🔝 Remuneración máxima: S/{maxima:,.0f}")
    
    # Con link de postulación
    cursor.execute("SELECT COUNT(*) FROM ofertas WHERE link_postulacion IS NOT NULL AND link_postulacion != ''")
    con_link = cursor.fetchone()[0]
    print(f"🔗 Con link de postulación: {con_link}")
    
    # Top 10 mejores sueldos
    print("\n" + "-"*60)
    print("🏆 TOP 10 MEJORES SUELDOS:")
    print("-"*60)
    cursor.execute("""
        SELECT puesto, entidad, remuneracion, ubicacion, link_postulacion
        FROM ofertas 
        WHERE remuneracion > 0 AND activo = 1
        ORDER BY remuneracion DESC 
        LIMIT 10
    """)
    for i, row in enumerate(cursor.fetchall(), 1):
        link = "✅" if row["link_postulacion"] else "❌"
        print(f"{i:2}. S/{row['remuneracion']:,.0f} | {row['puesto'][:35]}...")
        print(f"    📍 {row['ubicacion'][:30]} | 🏢 {row['entidad'][:30]}...")
        print(f"    🔗 Link: {link}")
        print()
    
    # Por ubicación
    print("-"*60)
    print("📍 OFERTAS POR UBICACIÓN (Top 10):")
    print("-"*60)
    cursor.execute("""
        SELECT ubicacion, COUNT(*) as cantidad, AVG(remuneracion) as promedio
        FROM ofertas 
        WHERE activo = 1
        GROUP BY ubicacion 
        ORDER BY cantidad DESC 
        LIMIT 10
    """)
    for row in cursor.fetchall():
        prom = f"S/{row['promedio']:,.0f}" if row['promedio'] else "N/A"
        print(f"   {row['ubicacion'][:35]:35} | {row['cantidad']:3} ofertas | Prom: {prom}")
    
    # Log de scraping
    print("\n" + "-"*60)
    print("📋 HISTORIAL DE SCRAPING:")
    print("-"*60)
    cursor.execute("""
        SELECT fecha_inicio, registros_nuevos, registros_actualizados, 
               registros_total, estado
        FROM scraping_log 
        ORDER BY fecha_inicio DESC 
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"   {row['fecha_inicio'][:16]} | Nuevos: {row['registros_nuevos']} | "
              f"Actualizados: {row['registros_actualizados']} | Total: {row['registros_total']} | {row['estado']}")
    
    print("\n" + "="*60 + "\n")
    
    conn.close()

if __name__ == "__main__":
    consultar()