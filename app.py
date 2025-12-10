        else:
            st.info("Enable Dhan above to view and refresh your portfolio.")

    elif page == "📊 Dhan Analysis":
        st.subheader("📊 Dhan Holdings – Multi‑Timeframe AI Analysis")

        if not st.session_state.get("dhan_enabled", False):
            st.info("Enable and connect Dhan on the 🤝 Dhan page first to see analysis here.")
        else:
            df_port, total_pnl = format_dhan_portfolio_table()
            if df_port is None or df_port.empty:
                st.info("No Dhan holdings/positions fetched yet.")
            else:
                st.markdown(
                    "This page analyses each Dhan holding across BTST, Weekly and Monthly timeframes and "
                    "gives an AI-style BUY/SELL/HOLD view, along with how far CMP is from the recommended target price."
                )
                st.markdown("---")

                all_rows = []
                prog = st.progress(0.0)
                for i, row in df_port.iterrows():
                    stock = str(row.get("Stock", "")).strip().upper()
                    if not stock:
                        continue
                    cmp_dhan = float(row.get("CMP", 0.0) or 0.0)

                    analysis = analyze_dhan_stock_all_periods(stock, cmp_dhan)
                    periods_info = analysis.get("periods", {})
                    ai_overall = analysis.get("ai_overall", "NO_SIGNAL")

                    for p in ["BTST", "Weekly", "Monthly"]:
                        info = periods_info.get(p)
                        if not info:
                            continue
                        gap_abs = info.get("cmp_gap_abs")
                        gap_pct = info.get("cmp_gap_pct")

                        all_rows.append({
                            "Stock": stock,
                            "Timeframe": p,
                            "CMP (from analysis)": info.get("cmp_ai"),
                            "Target 1": info.get("target_1"),
                            "CMP → Target Δ (₹)": gap_abs,
                            "CMP → Target Δ (%)": gap_pct,
                            "Signal Strength": info.get("signal_strength"),
                            "Score": info.get("score"),
                            "Key Strategies": info.get("strategies"),
                            "AI Buy/Sell/Hold": ai_overall,
                        })

                    prog.progress((i + 1) / len(df_port))
                prog.empty()

                if not all_rows:
                    st.info("No strong BTST/Weekly/Monthly signals detected for current Dhan holdings right now.")
                else:
                    df_analysis = pd.DataFrame(all_rows)
                    df_analysis = df_analysis.sort_values(["AI Buy/Sell/Hold", "Score"], ascending=[True, False])
                    st.dataframe(df_analysis, use_container_width=True, hide_index=True)

                    st.caption(
                        "AI Buy/Sell/Hold is derived from combined signals across BTST, Weekly and Monthly "
                        "technical setups for each stock."
                    )
