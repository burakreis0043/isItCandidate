import os
import json
import re
from typing import Dict, Any, List, Optional
from pypdf import PdfReader
import ollama


class CVScreeningEngine:
    """
    Şirket politikalarına ve iş ilanı kriterlerine göre
    aday CV'lerini yerel Qwen 2.5:14B modeliyle analiz eden,
    puanlayan ve yapısal JSON raporu üreten İK tarama motoru.
    """

    def __init__(self, model_name: str = "qwen2.5:14b"):
        self.model_name = model_name

    def extract_text_from_file(self, file_path: str) -> str:
        """PDF veya metin tabanlı CV dosyasının tüm içeriğini çıkarır."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            try:
                reader = PdfReader(file_path)
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t:
                        pages_text.append(f"--- Sayfa {idx + 1} ---\n{t.strip()}")
                return "\n\n".join(pages_text)
            except Exception as e:
                return f"[PDF Okuma Hatası: {str(e)}]"
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin-1") as f:
                    return f.read()
            except Exception as e:
                return f"[Metin Okuma Hatası: {str(e)}]"

    def analyze_cv(
        self,
        cv_text: str,
        job_title: str,
        mandatory_requirements: str,
        bonus_requirements: str,
        company_policies: str,
        file_name: str = "Aday_CV.pdf"
    ) -> Dict[str, Any]:
        """
        Bir aday CV'sini şirket kriterlerine göre analiz eder ve
        garantili JSON formatında puanlanmış İK raporu döner.
        """
        system_prompt = (
            "Sen çok uluslu ve kurumsal şirketlerde görev yapan kıdemli, adil ve objektif bir "
            "'Yetenek Kazanımı & İşe Alım Direktörü' (Talent Acquisition Director) ve Yapay Zeka Ekspertizisin.\n\n"
            "GÖREVİN:\n"
            "Verilen aday özgeçmişini (CV); şirket politikaları, zorunlu nitelikler ve tercih sebepleri ışığında "
            "titizlikle incelemek, puanlamak ve İK komitesi için karar raporu üretmektir.\n\n"
            "PUANLAMA VE DEĞERLENDİRME PRENSİPLERİ:\n"
            "1. Zorunlu nitelikler karşılanmıyorsa veya katı şirket politikası ihlal edilmişse aday 'REDDEDİLDİ' veya 'YEDEK ADAY' olmalı, puanı 65'i geçmemelidir.\n"
            "2. Zorunlu nitelikleri eksiksiz karşılayan, tecrübesi ve ek yetenekleri güçlü adaylara 80-100 arası puan verilmeli ve 'MÜLAKATA ÇAĞIR' denmelidir.\n"
            "3. Karar sadece üç seçenekten biri olabilir: 'MÜLAKATA ÇAĞIR', 'YEDEK ADAY' veya 'UYGUN DEĞİL'.\n"
            "4. Adayın eksik veya şüpheli görünen yönlerini test etmek için spesifik ve teknik 3 mülakat sorusu yaz.\n\n"
            "MUTLAKA VE SADECE AŞAĞIDAKİ GEÇERLİ JSON FORMATINDA YANIT VER (JSON DIŞINDA HİÇBİR AÇIKLAMA YA DA METİN YAZMA):\n"
            "{\n"
            '  "candidate_name": "Adayın Adı Soyadı (CV\'de yazmıyorsa Dosya Adından çıkar)",\n'
            '  "current_title": "Adayın mevcut unvanı veya uzmanlık alanı",\n'
            '  "experience_years": "Tahmini toplam tecrübe (Örn: 4 Yıl)",\n'
            '  "suitability_score": 0 ile 100 arasında tam sayı puan,\n'
            '  "verdict": "MÜLAKATA ÇAĞIR" veya "YEDEK ADAY" veya "UYGUN DEĞİL",\n'
            '  "policy_violation": true veya false (Şirketin katı kurallarını ihlal ediyor mu?),\n'
            '  "matched_requirements": ["Karşılanan Kriter 1", "Karşılanan Kriter 2", ...],\n'
            '  "missing_or_gap_requirements": ["Eksik Kriter 1 (nedeniyle birlikte)", ...],\n'
            '  "top_strengths": ["Adayın en güçlü öne çıkan yönü 1", "Yön 2", ...],\n'
            '  "potential_risks": ["Risk veya soru işareti 1", ...],\n'
            '  "executive_summary": "İK yöneticisi için 2-3 cümlelik net, profesyonel karar özeti",\n'
            '  "tailored_interview_questions": [\n'
            '    "Mülakatta sorulacak spesifik soru 1",\n'
            '    "Mülakatta sorulacak spesifik soru 2",\n'
            '    "Mülakatta sorulacak spesifik soru 3"\n'
            '  ]\n'
            "}"
        )

        user_content = (
            f"=== DEĞERLENDİRİLECEK POZİSYON ===\n"
            f"Pozisyon Unvanı: {job_title}\n\n"
            f"=== ŞİRKET POLİTİKALARI & ÇALIŞMA ŞARTLARI ===\n"
            f"{company_policies if company_policies.strip() else 'Standart şirket kuralları geçerlidir.'}\n\n"
            f"=== ZORUNLU GEREKSİNİMLER ===\n"
            f"{mandatory_requirements if mandatory_requirements.strip() else 'Genel pozisyon gereksinimleri.'}\n\n"
            f"=== TERCİH SEBEBİ (BONUS) NİTELİKLER ===\n"
            f"{bonus_requirements if bonus_requirements.strip() else 'Ek bir tercih belirtilmemiştir.'}\n\n"
            f"=== ADAYIN CV METNİ (Dosya: {file_name}) ===\n"
            f"\"\"\"\n{cv_text[:12000]}\n\"\"\""  # Bağlam güvenliği için ilk 12000 karakter
        )

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                format="json",
                options={
                    "temperature": 0.15,
                    "top_p": 0.9
                }
            )

            content = response["message"]["content"].strip()
            
            # JSON temizleme (Markdown kod bloğu varsa arındırma)
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)
            result["file_name"] = file_name
            return result

        except Exception as e:
            # Fallback: JSON ayrıştırma veya model hatası durumunda
            return {
                "file_name": file_name,
                "candidate_name": file_name.replace(".pdf", "").replace(".txt", ""),
                "current_title": "Belirtilmemiş",
                "experience_years": "Bilinmiyor",
                "suitability_score": 50,
                "verdict": "YEDEK ADAY",
                "policy_violation": False,
                "matched_requirements": ["Analiz sırasında hata oluştu"],
                "missing_or_gap_requirements": [f"Hata detayı: {str(e)}"],
                "top_strengths": ["Manuel inceleme gereklidir"],
                "potential_risks": ["Otomatik puanlama tamamlanamadı"],
                "executive_summary": f"Sistem yanıtı ayrıştırırken bir sorunla karşılaştı: {str(e)}",
                "tailored_interview_questions": ["Adayın özgeçmişi manuel incelenmeli."]
            }
