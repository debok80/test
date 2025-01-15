import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

def init_database():
    """Initialisiert die SQLite Datenbank"""
    conn = sqlite3.connect('verbrauchswerte.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS verbrauchswerte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum DATE NOT NULL,
            strom_kwh FLOAT,
            fernwaerme_mwh FLOAT,
            wasser_m3 FLOAT,
            bemerkung TEXT
        )
    ''')
    conn.commit()
    conn.close()

def import_csv_data():
    """Importiert die Daten aus der Ablesewerte.csv Datei"""
    try:
        # Lese die CSV-Datei, überspringe die ersten 2 Zeilen
        df = pd.read_csv('Ablesewerte.csv', 
                        skiprows=2,
                        sep=',',
                        encoding='utf-8',
                        decimal='.',
                        thousands=None)
        
        # Wähle nur die relevanten Spalten
        df = df[['Datum', 'Strom(kWh)', 'Fernwärme(MWh)', 'Wasser(m³)']]
        
        # Entferne Zeilen, wo alle Werte fehlen
        df = df.dropna(how='all')
        
        # Konvertiere Datum
        df['Datum'] = pd.to_datetime(df['Datum'], format='%d/%m/%Y')
        
        # Konvertiere numerische Werte
        df['Strom(kWh)'] = pd.to_numeric(df['Strom(kWh)'], errors='coerce')
        df['Fernwärme(MWh)'] = pd.to_numeric(df['Fernwärme(MWh)'], errors='coerce')
        df['Wasser(m³)'] = pd.to_numeric(df['Wasser(m³)'], errors='coerce')
        
        # Entferne Zeilen mit fehlenden Werten
        df = df.dropna()
        
        # Spaltennamen für Datenbank anpassen
        df_to_save = df.rename(columns={
            'Datum': 'datum',
            'Strom(kWh)': 'strom_kwh',
            'Fernwärme(MWh)': 'fernwaerme_mwh',
            'Wasser(m³)': 'wasser_m3'
        })
        
        # Verbindung zur Datenbank
        conn = sqlite3.connect('verbrauchswerte.db')
        
        # Daten in die Datenbank schreiben
        df_to_save.to_sql('verbrauchswerte', conn, 
                         if_exists='append', 
                         index=False)
        
        conn.close()
        return len(df)
        
    except Exception as e:
        print(f"Fehler beim Import: {str(e)}")
        raise

def create_medium_plot(df, medium_name, y_column, title, y_axis_title):
    """Erstellt ein einzelnes Plot für ein Medium"""
    fig = px.line(df, 
                  title=title,
                  labels={'value': y_axis_title, 
                         'monat': 'Monat',
                         'variable': 'Jahr'},
                  height=400)
    
    fig.update_layout(
        xaxis_title="Monat",
        yaxis_title=y_axis_title,
        legend_title="Jahr",
        hovermode='x unified'
    )
    return fig

def calculate_trends(df):
    """Berechnet monatliche und jährliche Trends aus den Verbrauchsdaten"""
    # Konvertiere datum zu datetime falls noch nicht geschehen
    df = df.copy()
    df['datum'] = pd.to_datetime(df['datum'])
    
    # Sortiere nach Datum
    df = df.sort_values('datum')
    
    # Berechne Differenzen für jeden Zählerstand
    for column in ['strom_kwh', 'fernwaerme_mwh', 'wasser_m3']:
        df[f'{column}_diff'] = df[column].diff()
        
        # Setze Differenz für den 01.01.2022 auf NaN für Strom und Fernwärme
        if column in ['strom_kwh', 'fernwaerme_mwh']:
            zaehlerwechsel_maske = (df['datum'].dt.date == pd.to_datetime('2022-01-01').date())
            df.loc[zaehlerwechsel_maske, f'{column}_diff'] = None
    
    # Monatliche Trends (nur mit den Differenzwerten)
    monthly_trends = df.groupby([df['datum'].dt.year, df['datum'].dt.month]).agg({
        'strom_kwh_diff': 'sum',
        'fernwaerme_mwh_diff': 'sum',
        'wasser_m3_diff': 'sum'
    }).round(2)
    
    # Rename columns to remove '_diff' suffix
    monthly_trends.columns = ['strom_kwh', 'fernwaerme_mwh', 'wasser_m3']
    
    # Jährliche Trends (nur mit den Differenzwerten)
    yearly_trends = df.groupby(df['datum'].dt.year).agg({
        'strom_kwh_diff': 'sum',
        'fernwaerme_mwh_diff': 'sum',
        'wasser_m3_diff': 'sum'
    }).round(2)
    
    # Rename columns to remove '_diff' suffix
    yearly_trends.columns = ['strom_kwh', 'fernwaerme_mwh', 'wasser_m3']
    
    return monthly_trends, yearly_trends

def calculate_year_comparison(df):
    """Berechnet Jahresgesamtverbrauch und prozentuale Veränderungen"""
    # Konvertiere datum zu datetime falls noch nicht geschehen
    df = df.copy()
    df['datum'] = pd.to_datetime(df['datum'])
    
    # Sortiere nach Datum
    df = df.sort_values('datum')
    
    # Berechne Differenzen für jeden Zählerstand
    for column in ['strom_kwh', 'fernwaerme_mwh', 'wasser_m3']:
        df[f'{column}_diff'] = df[column].diff()
        
        # Setze Differenz für den 01.01.2022 auf NaN für Strom und Fernwärme
        if column in ['strom_kwh', 'fernwaerme_mwh']:
            zaehlerwechsel_maske = (df['datum'].dt.date == pd.to_datetime('2022-01-01').date())
            df.loc[zaehlerwechsel_maske, f'{column}_diff'] = None
    
    # Jahresgesamtverbrauch (nur mit den Differenzwerten)
    yearly_totals = df.groupby(df['datum'].dt.year).agg({
        'strom_kwh_diff': 'sum',
        'fernwaerme_mwh_diff': 'sum',
        'wasser_m3_diff': 'sum'
    }).round(2)
    
    # Rename columns to remove '_diff' suffix
    yearly_totals.columns = ['strom_kwh', 'fernwaerme_mwh', 'wasser_m3']
    
    # Prozentuale Veränderung zum Vorjahr
    yearly_changes = yearly_totals.pct_change() * 100
    
    return yearly_totals, yearly_changes

def main():
    st.title("Verbrauchswerte-Erfassung")
    
    # Initialisiere Datenbank
    init_database()
    
    # Erweitere Tabs um Analyse
    tab1, tab2, tab3, tab4 = st.tabs(["Eingabe", "Datenübersicht", "Grafische Auswertung", "Analyse"])
    
    with tab1:
        # Import-Button mit detaillierter Rückmeldung
        if st.button("Bestandsdaten importieren"):
            try:
                num_imported = import_csv_data()
                st.success(f"Import erfolgreich! {num_imported} Datensätze wurden importiert.")
                
                # Zeige Beispieldaten aus der Datenbank
                conn = sqlite3.connect('verbrauchswerte.db')
                sample = pd.read_sql_query('''
                    SELECT datum, strom_kwh, fernwaerme_mwh, wasser_m3 
                    FROM verbrauchswerte 
                    ORDER BY datum DESC 
                    LIMIT 5
                ''', conn)
                conn.close()
                
                st.write("Die letzten 5 importierten Einträge:")
                st.dataframe(sample)
                
            except Exception as e:
                st.error(f"Fehler beim Import: {str(e)}")
        
        # Eingabeformular
        with st.form("eingabe_form"):
            datum = st.date_input("Datum", datetime.now())
            strom = st.number_input("Stromverbrauch (kWh)", min_value=0.0, format="%.2f")
            fernwaerme = st.number_input("Fernwärme (kWh)", min_value=0.0, format="%.2f")
            wasser = st.number_input("Wasser (m³)", min_value=0.0, format="%.2f")
            bemerkung = st.text_area("Bemerkung")
            
            submitted = st.form_submit_button("Speichern")
            
            if submitted:
                conn = sqlite3.connect('verbrauchswerte.db')
                c = conn.cursor()
                c.execute('''
                    INSERT INTO verbrauchswerte (datum, strom_kwh, fernwaerme_mwh, wasser_m3, bemerkung)
                    VALUES (?, ?, ?, ?, ?)
                ''', (datum, strom, fernwaerme, wasser, bemerkung))
                conn.commit()
                conn.close()
                st.success("Daten wurden erfolgreich gespeichert!")
    
    with tab2:
        # Datenübersicht
        st.subheader("Gespeicherte Verbrauchswerte")
        df = pd.read_sql_query('SELECT * FROM verbrauchswerte', sqlite3.connect('verbrauchswerte.db'))
        
        # Convert datum to datetime before formatting
        df['datum'] = pd.to_datetime(df['datum'])
        df['datum'] = df['datum'].dt.strftime('%d.%m.%Y')
        
        # Zeige die Daten an
        st.dataframe(df, use_container_width=True)
        
        # Download-Button für CSV
        if not df.empty:
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download als CSV",
                data=csv,
                file_name="verbrauchswerte_export.csv",
                mime="text/csv"
            )

    with tab4:
        st.header("Verbrauchsanalyse")
        
        # Lade Daten
        df = pd.read_sql_query('SELECT * FROM verbrauchswerte', sqlite3.connect('verbrauchswerte.db'))
        
        if not df.empty:
            # Zeitraum-Auswahl
            st.subheader("Zeitraum-Analyse")
            years = sorted(pd.to_datetime(df['datum']).dt.year.unique())
            selected_years = st.multiselect(
                "Jahre auswählen",
                years,
                default=years[-2:] if len(years) >= 2 else years
            )
            
            if selected_years:
                df_filtered = df[pd.to_datetime(df['datum']).dt.year.isin(selected_years)]
                
                # Monatliche und Jährliche Trends
                monthly_trends, yearly_trends = calculate_trends(df_filtered)
                
                st.subheader("pro Jahr")
                st.dataframe(yearly_trends)
                
                # Visualisierung Jahresvergleich
                fig_yearly = px.bar(yearly_trends, 
                                  barmode='group',
                                  title='Jährlicher Durchschnittsverbrauch')
                st.plotly_chart(fig_yearly)
                
                st.subheader("Monatliche Durchschnittswerte")
                # Formatiere den Index für bessere Lesbarkeit
                monthly_display = monthly_trends.copy()
                monthly_display.index = monthly_display.index.map(lambda x: f"{x[0]}-{x[1]:02d}")
                st.dataframe(monthly_display)
                
                # Visualisierung monatlicher Trend
                fig_monthly = px.line(monthly_display, 
                                    title='Monatlicher Verbrauchstrend')
                st.plotly_chart(fig_monthly)
                
                # Jahresvergleich
                st.subheader("Jahresvergleich")
                yearly_totals, yearly_changes = calculate_year_comparison(df_filtered)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("Jahresgesamtverbrauch")
                    st.dataframe(yearly_totals)
                
                with col2:
                    st.write("Prozentuale Veränderung zum Vorjahr")
                    st.dataframe(yearly_changes.round(1))
                
                # Statistische Kennzahlen
                st.subheader("Statistische Kennzahlen")
                stats = df_filtered.agg({
                    'strom_kwh': ['mean', 'min', 'max', 'std'],
                    'fernwaerme_mwh': ['mean', 'min', 'max', 'std'],
                    'wasser_m3': ['mean', 'min', 'max', 'std']
                }).round(2)
                
                st.dataframe(stats)
                
                # Saisonale Analyse
                st.subheader("Saisonale Analyse")
                df_filtered['monat'] = pd.to_datetime(df_filtered['datum']).dt.month
                seasonal = df_filtered.groupby('monat').agg({
                    'strom_kwh': 'mean',
                    'fernwaerme_mwh': 'mean',
                    'wasser_m3': 'mean'
                }).round(2)
                
                fig_seasonal = px.line(seasonal, 
                                     title='Saisonaler Verbrauchsverlauf',
                                     labels={'monat': 'Monat'})
                st.plotly_chart(fig_seasonal)
                
            else:
                st.warning("Bitte wählen Sie mindestens ein Jahr aus.")
        else:
            st.warning("Keine Daten verfügbar für die Analyse.")

if __name__ == "__main__":
    main()
