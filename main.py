import flet as ft
import json
import os
import random
import time
import threading
import re

# --- AYARLAR ---
SORU_DOSYASI = "sorular.json" 
BILGI_DOSYASI = "pratik_bilgiler.json"

# --- RENK PALETİ ---
class Renk:
    bg = "#F0F4F8" 
    card = "#FFFFFF"
    primary = "#6C5CE7" 
    text = "#2D3436"
    sub_text = "#636E72"
    success = "#00B894"
    error = "#FF7675"
    bookmark = "#0984E3"
    white = "#FFFFFF"
    info_bg = "#DFE6E9"
    info_text = "#2D3436"
    report = "#B2BEC3"
    danger = "#D63031"
    shadow = "#E0E0E0"
    bar_bg = "#DFE6E9"

# --- TEMA ---
PALETTE_LIGHT = {k: v for k, v in Renk.__dict__.items() if not k.startswith('__')}
PALETTE_DARK = {
    "bg": "#121212", "card": "#1E1E1E", "primary": "#7B61FF",
    "text": "#FFFFFF", "sub_text": "#636E72", "success": "#00B894",
    "error": "#FF7675", "bookmark": "#FFA502", "white": "#FFFFFF",
    "info_bg": "#3E3829", "info_text": "#FFDA6A", "report": "#95a5a6",
    "danger": "#FF4757", "shadow": "#000000", "bar_bg": "#333333"
}

# --- MÜFREDAT ---
MUFREDAT = [
    "Coğrafi Konum", "Yerşekilleri ve Özellikleri", "İklim ve Bitki Örtüsü",
    "Nüfus ve Yerleşme", "Tarım, Hayvancılık ve Ormancılık",
    "Madenler, Enerji Kaynakları", "Ulaşım, Ticaret ve Turizm", "Coğrafi Bölgeleri"
]

# --- YEDEK BİLGİLER ---
BILGI_KARTLARI_YEDEK = [
    "Türkiye'nin en uzun kara sınırı Suriye iledir.",
    "Bor rezervinde dünyada 1. sıradayız.",
    "En fazla yağış alan ilimiz Rize'dir."
]

# --- DOSYA MOTORLARI ---
def sorulari_yukle():
    if os.path.exists(SORU_DOSYASI):
        try:
            with open(SORU_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def bilgileri_yukle():
    if os.path.exists(BILGI_DOSYASI):
        try:
            with open(BILGI_DOSYASI, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except: pass
    return BILGI_KARTLARI_YEDEK

def main(page: ft.Page):
    # --- DÜZELTME 1: Resim Yolu Hatası Giderildi ---
    # Mobilde C:/Users gibi yollar çalışmaz. Sadece dosya adını veriyoruz.
    # Flet, assets klasörüne otomatik bakar.
    page.window_icon = "icon.png" 
    # ---------------------------------------------

    page.title = "KPSS AI 2026"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = Renk.bg
    page.scroll = False 

    # --- STATE ---
    state = {
        "isim": "Öğrenci", "dogru": 0, "cozulen": 0,
        "kayitlar": [], "stats": {k: {"d":0, "y":0} for k in MUFREDAT},
        "tum_sorular": [], "pratik_bilgiler": [],
        "cozulen_idleri": [] 
    }

    # --- DÜZELTME 2: Yükleme Sistemi (Client Storage) ---
    def yukle():
        # Telefonun güvenli hafızasından verileri çek
        try:
            if page.client_storage.contains_key("kpss_data"):
                yuklenen = page.client_storage.get("kpss_data")
                state.update(yuklenen)
                
                # Eksik anahtarlar varsa tamamla (Eski sürümden geçenler için)
                if "cozulen_idleri" not in state: state["cozulen_idleri"] = []
                for k in MUFREDAT: 
                    if k not in state["stats"]: state["stats"][k] = {"d":0, "y":0}
        except Exception as e:
            print(f"Veri yükleme hatası: {e}")
            
        state["tum_sorular"] = sorulari_yukle()
        state["pratik_bilgiler"] = bilgileri_yukle()
    
    # --- DÜZELTME 3: Kayıt Sistemi (Client Storage) ---
    def kaydet():
        # Verileri telefonda güvenli bir alana kaydet (Dosya yazma hatasını önler)
        try:
            save_data = {k: state[k] for k in ["isim", "dogru", "cozulen", "kayitlar", "stats", "cozulen_idleri"]}
            page.client_storage.set("kpss_data", save_data)
        except Exception as e:
            print(f"Kayıt hatası: {e}")

    yukle()

    # --- YARDIMCI: POP-UP UYARI GÖSTER ---
    def uyari_goster(baslik, mesaj, ikon_renk=Renk.primary):
        dlg = ft.AlertDialog(
            title=ft.Text(baslik, color=Renk.text),
            content=ft.Text(mesaj, size=16, color=Renk.sub_text),
            actions=[
                ft.TextButton("Tamam", on_click=lambda e: page.close(dlg))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=Renk.card
        )
        page.open(dlg)

    # --- TEST DEĞİŞKENLERİ ---
    test_durumu = {
        "index": 0, "sorular": [], "aktif": False, "baslangic": 0, 
        "toplam_sure": 0, "test_dogru": 0, "hatali_konular": [], 
        "soru_havuzu": [], "havuz_index": 0, "yukleniyor": False, 
        "telafi_modu": False, "hedef_soru_sayisi": 20,
        "cevaplandi": False,
        "gecici_sonuclar": [] 
    }

    # --- ROUTER ---
    def router(route):
        page.views.clear()
        
        palet = PALETTE_DARK if page.theme_mode == ft.ThemeMode.DARK else PALETTE_LIGHT
        for k, v in palet.items(): setattr(Renk, k, v)
        page.bgcolor = Renk.bg

        gidilecek = page.route
        if gidilecek == "/": page.views.append(view_giris())
        elif gidilecek == "/home": page.views.append(view_home())
        elif gidilecek == "/test": page.views.append(view_test())
        elif gidilecek == "/sonuc": page.views.append(view_sonuc())
        elif gidilecek == "/profil": page.views.append(view_profil())
        elif gidilecek == "/info": page.views.append(view_info())
        page.update()

    def tema_degis(e):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        router(page.route) 

 # --- 1. GİRİŞ EKRANI (GÜNCELLENDİ: İÇERİK AŞAĞI KAYDIRILDI) ---
    def view_giris():
        # Buraya kendi sitenin linkini koyacaksın
        GIZLILIK_URL = "https://sites.google.com/view/kpss-ai-2026-privacy"

        isim_input = ft.TextField(
            label="İsminiz", 
            border_radius=15, 
            text_align="center", 
            bgcolor="white", 
            color="black",
            width=280, 
            text_size=16
        )
        
        def giris_yap(e):
            if isim_input.value:
                state["isim"] = isim_input.value
                kaydet()
                page.go("/home")
        
        return ft.View("/", bgcolor=Renk.bg, padding=0, controls=[
            ft.Container(
                expand=True,
                alignment=ft.alignment.center, 
                padding=40,
                content=ft.Column([
                    
                    # --- YENİ EKLENEN BOŞLUK (AŞAĞI İTMEK İÇİN) ---
                    # Bu değerle oynayarak (100, 150, 200) ne kadar aşağı ineceğini ayarlayabilirsin.
                    ft.Container(height=45), 
                    # -----------------------------------------------

                    # 1. LOGO / İKON
                    ft.Container(
                        content=ft.Icon("map", size=60, color=Renk.primary),
                        padding=20,
                        bgcolor=Renk.card,
                        border_radius=50,
                        shadow=ft.BoxShadow(blur_radius=10, color=Renk.primary)
                    ),
                    
                    ft.Container(height=20), 

                    # 2. BAŞLIKLAR
                    ft.Text("KPSS AI 2026", size=28, weight="bold", color=Renk.primary),
                    ft.Text("COĞRAFYA", size=36, weight="heavy", color=Renk.text),
                    ft.Text("HAZIR MISIN?", size=20, weight="w500", color=Renk.sub_text),

                    ft.Container(height=30), 

                    # 3. İSİM GİRİŞ ALANI
                    isim_input,

                    ft.Container(height=10), 

                    # 4. BAŞLA BUTONU
                    ft.ElevatedButton(
                        "BAŞLA", 
                        on_click=giris_yap, 
                        height=55, 
                        width=200, 
                        style=ft.ButtonStyle(
                            bgcolor=Renk.primary, 
                            color=Renk.white,
                            shape=ft.RoundedRectangleBorder(radius=15),
                            text_style=ft.TextStyle(size=18, weight="bold")
                        )
                    ),
                    
                    ft.Container(height=30), 

                    # 5. YAPAY ZEKA YAZISI
                    ft.Row([
                        ft.Icon("auto_awesome", color=Renk.primary, size=16),
                        ft.Text("Yapay Zeka Destekli", size=14, color=Renk.sub_text)
                    ], alignment="center", spacing=5),

                    # Bu, alttaki linki en dibe iter
                    ft.Container(expand=True), 

                    # 6. GİZLİLİK POLİTİKASI LİNKİ
                    ft.TextButton(
                        "Gizlilik Politikası ve Kullanıcı Sözleşmesi",
                        on_click=lambda _: page.launch_url(GIZLILIK_URL),
                        style=ft.ButtonStyle(
                            color=Renk.sub_text,
                            text_style=ft.TextStyle(size=11, weight="bold")
                        )
                    ),
                    ft.Container(height=10) # En altta biraz pay kalsın

                ], 
                # Hizalama Ayarları
                alignment=ft.MainAxisAlignment.CENTER, 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                spacing=5
                )
            )
        ])

# --- 2. ANA SAYFA (GÜNCELLENDİ: TAM ORTALAMA VE HİZALAMA) ---
    def view_home():
        d = state["dogru"]
        seviyeler = [(20, "Çırak 🥉"), (50, "Hırslı 🥈"), (100, "Uzman 🥇"), (250, "Profesör 🎓"), (500, "Duayen 📚"), (1000, "Efsane 👑")]
        rutbe = "Efsane 👑"; hedef = 10000 
        for lim, ad in seviyeler:
            if d < lim: rutbe = ad; hedef = lim; break
        
        kalan = max(0, hedef - d)
        oran = min(1, d / hedef if hedef > 0 else 0)
        basari = int((state["dogru"] / state["cozulen"]) * 100) if state["cozulen"] > 0 else 0

        def baslat_test(konu):
            if not state["tum_sorular"]:
                 uyari_goster("Hata", "Soru dosyası boş!", Renk.error)
                 return

            # --- HAVUZU OLUŞTURMA ---
            ham_havuz = []
            if konu == "KAYITLI": 
                ham_havuz = state["kayitlar"].copy()
            elif konu == "TÜMÜ": 
                ham_havuz = state["tum_sorular"]
            else:
                 hedef_konu = konu.lower()
                 ham_havuz = [s for s in state["tum_sorular"] if hedef_konu in s.get("konu", "").lower() or s.get("konu", "").lower() in hedef_konu]
            
            # --- FİLTRELEME ---
            if konu != "KAYITLI":
                cozulmus_kumesi = set(state["cozulen_idleri"])
                havuz = [s for s in ham_havuz if s["soru"] not in cozulmus_kumesi]
            else:
                havuz = ham_havuz

            if not havuz:
                if ham_havuz:
                     uyari_goster("Tebrikler! 🎉", "Bu konudaki tüm soruları başarıyla bitirdiniz.", Renk.success)
                else:
                     uyari_goster("Ups!", "Bu konuda henüz soru bulunamadı.", Renk.error)
                return

            # --- SORU SEÇİMİ ---
            secilen_sorular = []
            if konu == "TÜMÜ":
                temp_havuz = havuz.copy()
                for k_baslik in MUFREDAT:
                    konu_sorulari = [s for s in temp_havuz if s.get("konu") == k_baslik]
                    adet = 2
                    if len(konu_sorulari) > 0:
                        alincak = random.sample(konu_sorulari, min(len(konu_sorulari), adet))
                        secilen_sorular.extend(alincak)
                        for a in alincak: temp_havuz.remove(a)
                eksik = 20 - len(secilen_sorular)
                if eksik > 0:
                    if len(temp_havuz) >= eksik: secilen_sorular.extend(random.sample(temp_havuz, eksik))
                    else: secilen_sorular.extend(temp_havuz)
                random.shuffle(secilen_sorular)
            else:
                secilen_sorular = random.sample(havuz, min(len(havuz), 20))

            test_durumu.update({
                "konu": konu, "aktif": True, "baslangic": time.time(), "toplam_sure": 0, 
                "test_dogru": 0, "hatali_konular": [], "soru_havuzu": secilen_sorular, 
                "havuz_index": 0, "yukleniyor": False, "telafi_modu": False, 
                "hedef_soru_sayisi": len(secilen_sorular), "cevaplandi": False, "gecici_sonuclar": [] 
            })
            page.go("/test")

        # --- GRID VE KART TASARIMI ---
        grid = ft.Row(wrap=True, spacing=10, run_spacing=10, alignment=ft.MainAxisAlignment.CENTER)
        
        for konu in MUFREDAT:
            s = state["stats"].get(konu, {"d":0, "y":0})
            tot = s["d"] + s["y"]
            k_basari = int((s["d"]/tot)*100) if tot > 0 else 0

            hedef_konu = konu.lower()
            konu_sorulari = [s for s in state["tum_sorular"] if hedef_konu in s.get("konu", "").lower() or s.get("konu", "").lower() in hedef_konu]
            cozulmus_kumesi = set(state["cozulen_idleri"])
            kalan_sorular = [s for s in konu_sorulari if s["soru"] not in cozulmus_kumesi]
            kalan_sayi = len(kalan_sorular)

            etiket_renk = Renk.primary
            etiket_metin = f"{kalan_sayi} Soru"
            
            if kalan_sayi == 0 and len(konu_sorulari) > 0:
                etiket_renk = Renk.success
                etiket_metin = "Bitti ✔"
            elif len(konu_sorulari) == 0:
                etiket_renk = Renk.sub_text
                etiket_metin = "-"

            card = ft.Container(
                content=ft.Column([
                    ft.Text(konu, weight="bold", text_align="center", color=Renk.text, size=11, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Container(
                        content=ft.Text(etiket_metin, size=9, color="white", weight="bold"),
                        bgcolor=etiket_renk,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=5
                    ),
                    ft.Text(f"%{k_basari} Başarı", text_align="center", size=9, color=Renk.sub_text)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3), 
                bgcolor=Renk.card, border_radius=12, alignment=ft.alignment.center, 
                on_click=lambda e, k=konu: baslat_test(k), ink=True, 
                shadow=ft.BoxShadow(blur_radius=5, color=Renk.shadow), width=165, height=85 
            )
            grid.controls.append(card)

        def create_wide_btn(text, icon_name, bg_color, on_click):
            return ft.Container(
                content=ft.Row([
                    ft.Row([ft.Icon(icon_name, color="white", size=20), ft.Text(text, color="white", weight="bold", size=14)]),
                    ft.Icon("chevron_right", color="white", size=20)
                ], alignment="spaceBetween"),
                bgcolor=bg_color, padding=ft.padding.symmetric(horizontal=15), border_radius=12,
                on_click=on_click, height=60, shadow=ft.BoxShadow(blur_radius=5, color=Renk.shadow), ink=True,
                width=350 # Butonlara genişlik vererek ortalanmalarını garantiye aldık
            )
        
        # --- ANA İÇERİK KOLONU ---
        icerik_kolonu = ft.Column(
            controls=[
                ft.Container(height=30), 

                ft.Container(content=ft.Column([
                    ft.Row([
                        ft.Column([
                            ft.Text(f"Merhaba, {state['isim']}", size=20, weight="bold", color=Renk.text), 
                            ft.Text(f"Rütbe: {rutbe}", size=14, color=Renk.primary), 
                            ft.ProgressBar(value=oran, color=Renk.bookmark, bgcolor=Renk.bar_bg, height=8, border_radius=4)
                        ], expand=True),
                        ft.IconButton("person", icon_color=Renk.text, on_click=lambda _: page.go("/profil"), icon_size=24),
                        ft.IconButton("dark_mode", icon_color=Renk.text, on_click=tema_degis, icon_size=24)
                    ]),
                    ft.Text(f"{d} / {hedef} Doğru (Sonraki Rütbe İçin: {kalan})", size=12, color=Renk.sub_text, weight="bold")
                ]), padding=20),
                
                ft.Container(
                    gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=["#6C5CE7", "#a29bfe"]),
                    content=ft.Row([
                        ft.Stack([
                            ft.ProgressRing(value=basari/100, width=70, height=70, stroke_width=7, color="white", bgcolor="#4DFFFFFF"), 
                            ft.Container(content=ft.Text(f"%{basari}", weight="bold", size=18, color="white"), alignment=ft.alignment.center, width=70, height=70)
                        ]),
                        ft.Column([
                            ft.Row([ft.Icon("emoji_events", color="#FFEAA7", size=24), ft.Text("GENEL BAŞARI", weight="bold", color="white", size=16)], spacing=5),
                            ft.Text(f"{state['cozulen']} Soru Çözüldü", size=12, color="#DFE6E9")
                        ], alignment="center", spacing=2)
                    ], alignment="center", spacing=20), 
                    padding=20, margin=ft.margin.symmetric(horizontal=15), border_radius=20, shadow=ft.BoxShadow(blur_radius=10, color=Renk.primary)
                ),

                ft.Container(content=ft.Row([
                    ft.Text("Konular", size=18, weight="bold", color=Renk.text), 
                    ft.TextButton("💡 Pratik Bilgi", on_click=lambda _: page.go("/info"))
                ], alignment="spaceBetween"), padding=ft.padding.symmetric(horizontal=15, vertical=10)),
                
                ft.Container(content=grid, padding=ft.padding.symmetric(horizontal=15)),
                ft.Container(content=ft.Column([
                    create_wide_btn(f"Kaydedilenler ({len(state['kayitlar'])})", "bookmark", Renk.bookmark, lambda _: baslat_test("KAYITLI") if state['kayitlar'] else None), 
                    create_wide_btn("Karışık Deneme", "rocket_launch", Renk.primary, lambda _: baslat_test("TÜMÜ"))
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=20), # Buradaki hizalamayı da düzelttim
                ft.Container(height=50) 
            ],
            scroll=ft.ScrollMode.HIDDEN, 
            spacing=5,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER # İŞTE SİHİRLİ DOKUNUŞ BURASI!
        )

        return ft.View(
            "/home", 
            bgcolor=Renk.bg, 
            padding=0, 
            controls=[
                icerik_kolonu
            ]
        )

    # --- 3. TEST EKRANI ---
    def view_test():
        if not test_durumu["soru_havuzu"]:
            uyari_goster("Hata", "Soru havuzu boş!", Renk.error)
            page.go("/home")
            return ft.View("/test", controls=[])

        index = test_durumu["havuz_index"]
        if index >= len(test_durumu["soru_havuzu"]): 
            # TEST BİTTİ, KAYDET
            for sonuc in test_durumu["gecici_sonuclar"]:
                konu = sonuc["konu"]
                durum = sonuc["durum"]
                
                if konu not in state["stats"]: state["stats"][konu] = {"d":0, "y":0}
                if not test_durumu["telafi_modu"]:
                    state["cozulen"] += 1
                    if durum == "dogru":
                        state["dogru"] += 1
                        state["stats"][konu]["d"] += 1
                        if sonuc["soru_metni"] not in state["cozulen_idleri"]:
                            state["cozulen_idleri"].append(sonuc["soru_metni"])
                    else:
                        state["stats"][konu]["y"] += 1
            kaydet()
            test_durumu["aktif"] = False
            page.go("/sonuc")
            return ft.View("/test", controls=[])

        soru = test_durumu["soru_havuzu"][index]
        test_durumu["cevaplandi"] = False

        lbl_soru = ft.Text(soru["soru"], size=18, weight="bold", text_align="center", color=Renk.text)
        lbl_sayac = ft.Text(f"Soru: {index+1} / {test_durumu['hedef_soru_sayisi']}", weight="bold", color=Renk.text)
        
        baslangic_dk, baslangic_sn = divmod(test_durumu["toplam_sure"], 60)
        lbl_sure = ft.Text(f"⏱️ {baslangic_dk}:{baslangic_sn:02d}", color=Renk.primary, weight="bold")
        
        btn_siklar = []
        harfler = ["A", "B", "C", "D", "E"]

        scroll_container = ft.Column(
            spacing=15, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

        # --- ÇIKIŞ ONAYI PENCERESİ (GÜVENLİ VE HIZLI) ---
        def cikis_yap_onayla(e):
            # 1. Sayacı ve işlemleri durdur
            test_durumu["aktif"] = False
            
            # 2. Pencereyi kapat
            page.close(dlg_cikis)
            
            # 3. Yönlendir
            page.go("/home")
            
            # 4. Bildirim
            page.snack_bar = ft.SnackBar(ft.Text("Test iptal edildi."), bgcolor=Renk.info_text)
            page.snack_bar.open = True
            page.update()

        dlg_cikis = ft.AlertDialog(
            title=ft.Text("Testten Çıkılsın mı?", color=Renk.text),
            content=ft.Text("İlerlemen KAYDEDİLMEYECEK. Emin misin?", color=Renk.sub_text),
            actions=[
                ft.TextButton("Vazgeç", on_click=lambda e: page.close(dlg_cikis)),
                ft.TextButton("Evet, Çık", on_click=cikis_yap_onayla, style=ft.ButtonStyle(color=Renk.error))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=Renk.card
        )

        def cevapla(e, secilen_btn_index):
            test_durumu["cevaplandi"] = True
            
            dogru_sik_index = -1
            dogru_veri = soru["dogru"].strip()
            
            for i, sik in enumerate(soru["siklar"]):
                s_temiz = re.sub(r'^[A-Ea-e][\)\.]\s*', '', sik).strip().lower()
                d_temiz = re.sub(r'^[A-Ea-e][\)\.]\s*', '', dogru_veri).strip().lower()
                
                if s_temiz == d_temiz: dogru_sik_index = i; break
                if len(d_temiz) == 1 and sik.strip().upper().startswith(d_temiz.upper()): dogru_sik_index = i; break
                if len(d_temiz) > 2 and d_temiz in s_temiz: dogru_sik_index = i; break

            kullanici_dogru_bildi = (secilen_btn_index == dogru_sik_index)

            konu = soru.get("konu", "Genel")
            for k in MUFREDAT: 
                if k.lower() in konu.lower() or konu.lower() in k.lower(): konu = k; break
            
            sonuc_verisi = {
                "soru_metni": soru["soru"],
                "konu": konu,
                "durum": "dogru" if kullanici_dogru_bildi else "yanlis"
            }
            test_durumu["gecici_sonuclar"].append(sonuc_verisi)

            if kullanici_dogru_bildi:
                btn_siklar[secilen_btn_index].style = ft.ButtonStyle(bgcolor=Renk.success, color="white")
                test_durumu["test_dogru"] += 1
            else:
                btn_siklar[secilen_btn_index].style = ft.ButtonStyle(bgcolor=Renk.error, color="white")
                if not test_durumu["telafi_modu"]: 
                    test_durumu["hatali_konular"].append(konu)
                if dogru_sik_index != -1:
                    btn_siklar[dogru_sik_index].style = ft.ButtonStyle(bgcolor=Renk.success, color="white")
            
            btn_siklar[secilen_btn_index].content.content.color = "white"
            lbl_aciklama.value = soru.get('aciklama', 'Açıklama yok.')
            info_box.visible = True
            btn_sonraki.visible = True
            for b in btn_siklar: b.disabled = True
            page.update()
            try: scroll_container.scroll_to(offset=-1, duration=300, curve=ft.AnimationCurve.EASE_OUT); page.update()
            except: pass

        for i, s in enumerate(soru.get("siklar", [])):
            btn = ft.ElevatedButton(
                content=ft.Container(content=ft.Text(f"{harfler[i]}) {re.sub(r'^[A-Ea-e][\)\.]\s*', '', s)}", size=15, color=Renk.text, text_align="center"), padding=12, alignment=ft.alignment.center),
                width=350, 
                on_click=lambda e, idx=i: cevapla(e, idx), 
                data=s, 
                style=ft.ButtonStyle(bgcolor=Renk.card, shape=ft.RoundedRectangleBorder(radius=15), elevation=2, shadow_color=Renk.shadow)
            )
            btn_siklar.append(btn)

        lbl_aciklama = ft.Text("", color=Renk.text, size=15)
        info_box = ft.Container(visible=False, bgcolor=Renk.info_bg, border_radius=15, padding=20, content=ft.Column([ft.Row([ft.Icon("school", color=Renk.primary), ft.Text("ÇÖZÜM", weight="bold", color=Renk.primary)], spacing=10), ft.Divider(height=10, color="transparent"), lbl_aciklama], spacing=5))
        
        btn_sonraki = ft.ElevatedButton("SONRAKİ", visible=False, width=350, height=55, on_click=lambda e: (test_durumu.update({"havuz_index": index + 1}), router(None)), style=ft.ButtonStyle(bgcolor=Renk.primary, color="white"))
        
        kayitli_mi = any(s['soru'] == soru['soru'] for s in state['kayitlar'])
        def islem_kaydet(e):
            nonlocal kayitli_mi
            if kayitli_mi:
                state['kayitlar'] = [s for s in state['kayitlar'] if s['soru'] != soru['soru']]
                kayitli_mi = False; e.control.icon = "bookmark_border"; e.control.icon_color = Renk.sub_text; e.control.text = "Kaydet"
            else:
                state['kayitlar'].append(soru)
                kayitli_mi = True; e.control.icon = "bookmark"; e.control.icon_color = Renk.bookmark; e.control.text = "Kaydedildi"
            kaydet(); e.control.update()

        def rapor_penceresi(e):
            page.open(ft.AlertDialog(content=ft.Text("Bildirim Alındı", color=Renk.text), bgcolor=Renk.card))

        btn_kaydet = ft.TextButton("Kaydedildi" if kayitli_mi else "Kaydet", icon="bookmark" if kayitli_mi else "bookmark_border", icon_color=Renk.bookmark if kayitli_mi else Renk.sub_text, on_click=islem_kaydet)
        btn_bildir = ft.TextButton("Bildir", icon="flag", icon_color=Renk.report, on_click=rapor_penceresi)

        # --- TIMER LOOP (ZOMBİ ÖNLEYİCİ - FİNAL VERSİYON) ---
        def timer_loop():
            test_durumu["aktif"] = True
            
            while True:
                # 1. Kritik Güvenlik Kontrolü (Her döngü başında)
                if not test_durumu.get("aktif", False) or page.route != "/test":
                    break

                try:
                    if not test_durumu.get("cevaplandi", False):
                        time.sleep(1)
                        # Uyuduktan sonra TEKRAR kontrol et (En önemlisi bu!)
                        if not test_durumu.get("aktif", False) or page.route != "/test":
                            break
                            
                        test_durumu["toplam_sure"] += 1
                        dk, sn = divmod(test_durumu["toplam_sure"], 60)
                        lbl_sure.value = f"⏱️ {dk}:{sn:02d}"
                        lbl_sure.update() 
                    else:
                        # Cevap verilse bile, çıkış yapılırsa döngüyü kırmalıyız
                        time.sleep(0.5)
                        if not test_durumu.get("aktif", False) or page.route != "/test":
                            break
                except:
                    # Sayfa değiştiyse update hatası verir, döngüyü kır
                    break

        threading.Thread(target=timer_loop, daemon=True).start()

        scroll_container.controls = [
            ft.Container(height=10),
            ft.Container(content=lbl_soru, padding=20, bgcolor=Renk.card, border_radius=15, shadow=ft.BoxShadow(blur_radius=5, color=Renk.shadow), margin=ft.margin.symmetric(horizontal=10)),
            ft.Container(content=ft.Row([btn_kaydet, btn_bildir], alignment="spaceBetween"), padding=ft.padding.symmetric(horizontal=10)),
            ft.Column(btn_siklar, spacing=12),
            ft.Container(content=info_box, margin=ft.margin.symmetric(horizontal=10)),
            ft.Container(height=10),
            btn_sonraki,
            ft.Container(height=100)
        ]

        return ft.View(
            "/test", 
            bgcolor=Renk.bg, 
            padding=0,
            controls=[
                ft.SafeArea(
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                padding=ft.padding.all(20),
                                content=ft.Row([ft.IconButton("close", icon_color=Renk.text, on_click=lambda _: page.open(dlg_cikis)), lbl_sayac, lbl_sure], alignment="spaceBetween"),
                                bgcolor=Renk.bg
                            ),
                            scroll_container
                        ],
                        spacing=0,
                        expand=True
                    ),
                    expand=True
                )
            ]
        )

    # --- 4. SONUÇ EKRANI ---
    def view_sonuc():
        test_durumu["aktif"] = False
        dk, sn = divmod(test_durumu["toplam_sure"], 60)
        yanlis = test_durumu["hedef_soru_sayisi"] - test_durumu["test_dogru"]
        hatali = list(set(test_durumu["hatali_konular"]))

        def yeni_test(e): 
            eski_konu = test_durumu.get("konu", "TÜMÜ")
            if eski_konu == "Telafi": eski_konu = "TÜMÜ"

            ham_havuz = []
            if eski_konu == "KAYITLI": ham_havuz = state["kayitlar"].copy()
            elif eski_konu == "TÜMÜ": ham_havuz = state["tum_sorular"]
            else:
                hedef = eski_konu.lower()
                ham_havuz = [s for s in state["tum_sorular"] if hedef in s.get("konu", "").lower() or s.get("konu", "").lower() in hedef]

            if eski_konu != "KAYITLI":
                cozulmus_kumesi = set(state["cozulen_idleri"])
                havuz = [s for s in ham_havuz if s["soru"] not in cozulmus_kumesi]
            else:
                havuz = ham_havuz

            if not havuz:
                if ham_havuz:
                     uyari_goster("Tebrikler! 🎉", "Bu konudaki tüm sorular bitti!", Renk.success)
                else:
                     uyari_goster("Ups!", "Soru bulunamadı.", Renk.error)
                return

            random.shuffle(havuz)
            secilen = havuz[:20]

            test_durumu.update({
                "konu": eski_konu, "aktif": True, "baslangic": time.time(), "toplam_sure": 0, 
                "test_dogru": 0, "hatali_konular": [], "soru_havuzu": secilen, "havuz_index": 0, 
                "yukleniyor": False, "telafi_modu": False, "hedef_soru_sayisi": len(secilen), "cevaplandi": False,
                "gecici_sonuclar": []
            })
            page.go("/test")
            
        def telafi_et(e): 
            if not hatali: return
            
            ham_havuz = [s for s in state["tum_sorular"] if s.get("konu") in hatali]
            cozulmus_kumesi = set(state["cozulen_idleri"])
            havuz = [s for s in ham_havuz if s["soru"] not in cozulmus_kumesi]

            if not havuz:
                uyari_goster("Harika!", "Hatalı olduğun konulardaki tüm soruları başarıyla tamamladın!", Renk.success)
                return

            random.shuffle(havuz)
            secilen = havuz[:20]

            test_durumu.update({
                "konu": "Telafi", "aktif": True, "baslangic": time.time(), "toplam_sure": 0, 
                "test_dogru": 0, "hatali_konular": [], "soru_havuzu": secilen, "havuz_index": 0, 
                "yukleniyor": False, "telafi_modu": True, "hedef_soru_sayisi": len(secilen), "cevaplandi": False,
                "gecici_sonuclar": []
            })
            page.go("/test")

        if hatali:
            baslik_mesaj = "Geliştirilmesi Gereken Konular:"
            oneri_icerik = ft.Column([
                ft.Text(baslik_mesaj, color=Renk.text, size=14, weight="bold"),
                ft.Divider(height=10, color="transparent"),
                *[ft.Row([ft.Icon("arrow_right", color=Renk.danger, size=16), ft.Text(h, color=Renk.text, size=13)], spacing=5) for h in hatali]
            ], spacing=5)
        else:
            oneri_icerik = ft.Column([
                ft.Icon("verified", color=Renk.success, size=40),
                ft.Text("Tebrikler! Hiç eksiğin yok.", color=Renk.success, weight="bold")
            ], horizontal_alignment="center", alignment="center")

        return ft.View("/sonuc", bgcolor=Renk.bg, padding=0, controls=[
            ft.SafeArea(
                content=ft.Column(
                    controls=[
                        ft.Container(height=20),
                        ft.Icon("emoji_events", size=60, color=Renk.primary), 
                        ft.Text("Test Tamamlandı!", size=22, weight="bold", color=Renk.text),
                        ft.Text(f"Süre: {dk}dk {sn}sn", color=Renk.sub_text, size=12),
                        
                        ft.Divider(height=10, color="transparent"),

                        ft.Row([
                            ft.Column([ft.Text(f"{test_durumu['test_dogru']}", size=28, color=Renk.success, weight="bold"), ft.Text("DOĞRU", size=10, color=Renk.text)], horizontal_alignment="center"), 
                            ft.Container(width=30), 
                            ft.Column([ft.Text(f"{yanlis}", size=28, color=Renk.error, weight="bold"), ft.Text("YANLIŞ", size=10, color=Renk.text)], horizontal_alignment="center")
                        ], alignment="center"),
                        
                        ft.Divider(height=20, color="transparent"),
                        
                        ft.Container(
                            content=oneri_icerik, 
                            padding=15, 
                            bgcolor=Renk.card, 
                            border_radius=10, 
                            width=350, 
                            shadow=ft.BoxShadow(blur_radius=2, color=Renk.shadow)
                        ),
                        
                        ft.Divider(height=20, color="transparent"),

                        ft.ElevatedButton(
                            "Eksiklerimi Kapat 🧠", 
                            bgcolor=Renk.danger, color="white", width=300, height=45, 
                            visible=len(hatali)>0, on_click=telafi_et
                        ),
                        ft.Container(height=5),
                        ft.ElevatedButton(
                            "Aynı Konudan Devam 🚀", 
                            bgcolor=Renk.success, color="white", width=300, height=45, 
                            on_click=yeni_test
                        ),
                        ft.Container(height=5),
                        ft.ElevatedButton(
                            "Ana Sayfa 🏠", 
                            bgcolor=Renk.primary, color="white", width=300, height=45, 
                            on_click=lambda _: page.go("/home")
                        ),
                        
                        ft.Container(height=50)
                    ],
                    horizontal_alignment="center",
                    scroll=ft.ScrollMode.AUTO,
                    expand=True
                ),
                expand=True
            )
        ])

    # --- 5. PROFİL EKRANI ---
    def view_profil():
        # --- LİNK AYARI ---
        # Google Sites üzerinden oluşturduğun linki ileride buraya yapıştıracaksın.
        GIZLILIK_URL = "https://sites.google.com/view/kpss-ai-2026-privacy" 

        isim_field = ft.TextField(value=state["isim"], hint_text="İsminizi giriniz...", border_radius=12, bgcolor=Renk.bg, border_color="transparent", filled=True, prefix_icon="person", color=Renk.text, content_padding=20)
        
        def kaydet_isim(e):
            state["isim"] = isim_field.value
            kaydet()
            e.control.text = "Kaydedildi! ✅"
            e.control.bgcolor = Renk.success
            e.control.update()
            def revert():
                time.sleep(1)
                try:
                    e.control.text = "Değişiklikleri Kaydet"
                    e.control.bgcolor = Renk.primary
                    e.control.update()
                except: pass
            threading.Thread(target=revert, daemon=True).start()

        def sifirla_onay(e):
            # Client Storage'ı temizle
            try: page.client_storage.clear()
            except: pass
            
            state.update({"isim":"Öğrenci", "dogru":0, "cozulen":0, "kayitlar":[], "stats":{k: {"d":0, "y":0} for k in MUFREDAT}, "cozulen_idleri": []})
            page.close(dlg_modal)
            page.go("/home")
            page.snack_bar = ft.SnackBar(ft.Text("Tüm ilerleme sıfırlandı!"), bgcolor=Renk.success)
            page.snack_bar.open = True
            page.update()

        dlg_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Emin misin?", color=Renk.text),
            content=ft.Text("Tüm istatistiklerin ve çözdüğün sorular sıfırlanacak.", color=Renk.sub_text),
            actions=[
                ft.TextButton("Vazgeç", on_click=lambda _: page.close(dlg_modal)),
                ft.TextButton("Sıfırla", on_click=sifirla_onay, style=ft.ButtonStyle(color=Renk.error))
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=Renk.card
        )

        return ft.View("/profil", bgcolor=Renk.bg, padding=0, controls=[
            ft.SafeArea(content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([ft.IconButton("arrow_back", icon_color=Renk.text, on_click=lambda _: page.go("/home")), ft.Text("Profil Ayarları", size=20, weight="bold", color=Renk.text)]),
                    ft.Divider(height=20, color="transparent"),
                    ft.Container(
                        padding=20, bgcolor=Renk.card, border_radius=20, shadow=ft.BoxShadow(blur_radius=10, color=Renk.shadow),
                        content=ft.Column([
                            ft.Text("Görünen İsim", weight="bold", color=Renk.text),
                            isim_field,
                            ft.Container(height=10),
                            ft.ElevatedButton("Değişiklikleri Kaydet", icon="save", bgcolor=Renk.primary, color="white", width=400, height=50, on_click=kaydet_isim)
                        ])
                    ),
                    ft.Container(expand=True),
                    ft.ElevatedButton("Tüm İlerlemeyi Sıfırla", icon="delete_forever", bgcolor=Renk.danger, color="white", width=400, height=50, on_click=lambda _: page.open(dlg_modal)),
                    ft.Container(height=10),
                    
                    # --- GÜNCELLENEN BUTON ---
                    # Tıklandığında tarayıcıyı açıp belirlediğin linke gider.
                    ft.Row([
                        ft.TextButton("Gizlilik Politikası ve Kullanım Şartları", on_click=lambda _: page.launch_url(GIZLILIK_URL))
                    ], alignment="center")
                ])
            ))
        ])

    # --- 6. PRATİK BİLGİ ---
    def view_info():
        if not state["pratik_bilgiler"]:
            state["pratik_bilgiler"] = BILGI_KARTLARI_YEDEK
            
        mevcut_bilgi = random.choice(state["pratik_bilgiler"])
        t_bilgi = ft.Text(mevcut_bilgi, size=20, text_align="center", color=Renk.text)
        
        def degistir(e):
            t_bilgi.value = random.choice(state["pratik_bilgiler"])
            t_bilgi.update()

        return ft.View("/info", bgcolor=Renk.bg, padding=0, controls=[
            ft.SafeArea(content=ft.Container(
                padding=20, 
                content=ft.Column([
                    ft.Row([ft.Text("Pratik Bilgi", size=20, color=Renk.text), ft.IconButton("close", icon_color=Renk.text, on_click=lambda _: page.go("/home"))], alignment="spaceBetween"),
                    ft.Container(expand=True, content=t_bilgi, alignment=ft.alignment.center, padding=30, bgcolor=Renk.card, border_radius=20, shadow=ft.BoxShadow(blur_radius=10, color=Renk.shadow)),
                    ft.Container(content=ft.ElevatedButton("Yeni Bilgi", icon="autorenew", bgcolor=Renk.primary, color="white", width=400, height=60, on_click=degistir), padding=ft.padding.only(bottom=20))
                ])
            ))
        ])

    page.on_route_change = router
    page.go("/" if state["isim"] == "Öğrenci" else "/home")

ft.app(target=main, assets_dir="assets")