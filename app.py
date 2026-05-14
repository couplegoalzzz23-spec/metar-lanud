# --- INTERFACE ---
st.title("✈️ QAM Generator")
st.write("Sesuai Standar Markas Besar Angkatan Udara")

# Pilihan Mode Operasional
mode = st.radio("Pilih Mode Operasional:", ["📡 Tarik Otomatis (Internet)", "⌨️ Input Manual (Radio/Internal)"])

if mode == "📡 Tarik Otomatis (Internet)":
    icao = st.text_input("Masukkan Kode ICAO (Contoh: WIBB, WIHH):", value="WIBB").upper()
    
    if st.button("Tarik Data & Generate PDF"):
        with st.spinner("Mengambil data cuaca terbaru..."):
            raw_metar = get_metar_raw(icao)
            if raw_metar:
                st.success("Data Berhasil Ditarik!")
                st.code(raw_metar)
                
                parsed = parse_metar(raw_metar)
                pdf_bytes = create_pdf(parsed, icao)
                
                st.download_button(
                    label="📥 Download PDF QAM",
                    data=pdf_bytes,
                    file_name=f"QAM_{icao}_{datetime.now().strftime('%H%M')}Z.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Data tidak tersedia di server publik. Silakan gunakan Mode Input Manual jika Anda memiliki sandi METAR internal.")

else:
    # MODE MANUAL: Untuk Lanud Militer tertutup atau saat internet gangguan
    st.info("Gunakan mode ini jika data dikirim via komunikasi internal TNI AU.")
    icao_manual = st.text_input("Kode ICAO Pangkalan:", value="WIAJ").upper()
    raw_manual = st.text_area("Masukkan Sandi METAR (Paste di sini):", placeholder="Contoh: WIAJ 140500Z 19004KT 9999 SCT010 32/23 Q1007 NOSIG")
    
    if st.button("Generate PDF dari Input Manual"):
        if raw_manual and icao_manual:
            parsed = parse_metar(raw_manual)
            pdf_bytes = create_pdf(parsed, icao_manual)
            
            st.success("PDF berhasil dibuat dari data manual!")
            st.download_button(
                label="📥 Download PDF QAM",
                data=pdf_bytes,
                file_name=f"QAM_{icao_manual}_MANUAL_{datetime.now().strftime('%H%M')}Z.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("Pastikan ICAO dan Sandi METAR sudah diisi.")
