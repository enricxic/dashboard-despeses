import sys  
text = open('app.py', 'r', encoding='utf-8').read()  
start_str = '            with subtab_gen:'  
end_str = '        except Exception as e:\n            st.error(f\x22Error carregant Menjar: {e}\x22)'  
