                 titulo_filtro_excel = filtro_obra_rel if filtro_obra_rel != "Todas" else "Todas as Obras"
                excel_bytes = gerar_excel_relatorio(df_tabela, titulo_filtro_excel)
                st.download_button(
                    label="Baixar relatório em Excel",
                    data=excel_bytes,
                    file_name=f"relatorio_producao_{datetime.now(FUSO_BR).strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_rel_xlsx"
                )

            # ── Seção: OPs Avulsas ────────────────────────────────
            st.markdown("---")
            with st.expander("OPs Avulsas cadastradas", expanded=False):
                df_avulsas = df_banco_micro_rel[df_banco_micro_rel['EDT_Vinculado'].str.startswith('AVULSO', na=False)].copy() if not df_banco_micro_rel.empty else pd.DataFrame()
                if filtro_obra_rel != "Todas" and not df_avulsas.empty:
                    df_avulsas = df_avulsas[df_avulsas['Obra_Vinculada'] == filtro_obra_rel]
                if df_avulsas.empty:
                    st.info("Nenhuma OP avulsa encontrada.")
                else:
                    cols_av = ['Obra_Vinculada','Num_OP','Tipo_Material','Qtd_Caixas','M2_Item',
                               'Data_Producao_Programada','Data_Limite_Obra','Status_Item','Romaneio_Chapas']
                    df_avulsas = df_avulsas[cols_av].copy()
                    df_avulsas.columns = ['Obra','OP','Material','Caixas','m²','Ini Prod.','Limite','Status','Detalhes']
                    for col_dt in ['Ini Prod.','Limite']:
                        df_avulsas[col_dt] = pd.to_datetime(df_avulsas[col_dt], errors='coerce').dt.strftime('%d/%m/%Y')
                    st.dataframe(df_avulsas.style.format({'m²': '{:.2f}'}), hide_index=True, use_container_width=True)
                    st.caption(f"{len(df_avulsas)} OP(s) avulsa(s) encontrada(s).")

