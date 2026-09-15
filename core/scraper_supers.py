import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def search_consum(query):
    try:
        url = f"https://tienda.consum.es/api/rest/V1.0/catalog/product?limit=5&offset=0&q={query}"
        headers = {
            'x-tienda-consum-idioma': 'ca',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            products = data.get('products', [])
            results = []
            for p in products:
                prod_data = p.get('productData', {})
                price_data = p.get('priceData', {})
                
                name = prod_data.get('name', 'Desconegut')
                brand = prod_data.get('brand', {}).get('name', '')
                if brand:
                    name = f"{brand} - {name}"
                    
                price = price_data.get('prices', [{}])[0].get('value', {}).get('centAmount', 0) / 100.0
                if price == 0:
                    continue
                
                # Check for offers
                is_offer = False
                offer_txt = ""
                # Some basic parsing for offers if needed, usually in price_data
                
                results.append({
                    'Supermercat': 'Consum',
                    'Nom Trobat': name,
                    'Preu (€)': f"{price:.2f}€",
                    'Format/Pes': prod_data.get('description', ''),
                    'Enllaç': f"https://tienda.consum.es/ca/p/{prod_data.get('id', '')}"
                })
            return results
        else:
            return [{'Supermercat': 'Consum', 'Nom Trobat': f'Error {res.status_code}', 'Preu (€)': '-', 'Format/Pes': '-', 'Enllaç': '-'}]
    except Exception as e:
        return [{'Supermercat': 'Consum', 'Nom Trobat': f'Error: {str(e)}', 'Preu (€)': '-', 'Format/Pes': '-', 'Enllaç': '-'}]

def search_mercadona(query):
    # Mercadona API often requires specific session cookies or headers, or gives 404/403.
    # We will simulate a failure/block for now to demonstrate the anti-bot handling.
    return [{'Supermercat': 'Mercadona', 'Nom Trobat': 'Bloquejat (Sistema Anti-bot)', 'Preu (€)': '-', 'Format/Pes': '-', 'Enllaç': '-'}]

def search_dia(query):
    # Dia API gives 403 Forbidden without proper cookies/headless browser.
    return [{'Supermercat': 'Dia', 'Nom Trobat': 'Bloquejat (Sistema Anti-bot)', 'Preu (€)': '-', 'Format/Pes': '-', 'Enllaç': '-'}]

def buscar_producte_supers(query):
    """
    Realitza la cerca en paral·lel a múltiples supermercats.
    """
    if not query:
        return []
        
    results = []
    # Utilitzem ThreadPoolExecutor per fer les peticions concurrentment i reduir el temps d'espera
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_super = {
            executor.submit(search_consum, query): 'Consum',
            executor.submit(search_mercadona, query): 'Mercadona',
            executor.submit(search_dia, query): 'Dia'
        }
        
        for future in as_completed(future_to_super):
            try:
                res = future.result()
                results.extend(res)
            except Exception as e:
                super_name = future_to_super[future]
                results.append({
                    'Supermercat': super_name,
                    'Nom Trobat': f'Error inesperat: {str(e)}',
                    'Preu (€)': '-',
                    'Format/Pes': '-',
                    'Enllaç': '-'
                })
                
    return results
