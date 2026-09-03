# TechStore product catalog

Canonical catalog for the synthetic generator. On implementation, copy to `data/company/product_catalog.yaml`.

**Rules**

- Exactly **10 products per category** (180 SKUs total).
- Each row: `name`, `category_slug`, `sku`. **No `subcategory_slug` on products** — FK only to top-level category.
- `public_id` (`PRD-00001`) assigned deterministically at seed time (category order, then product order).
- **`unit_price`:** omit in yaml — generator draws from `company.yaml` `price_bands` + seeded RNG (deterministic per SKU).
- **`final_sale`:** mark **one SKU per category** as outlet/clearance (policy tests).
- **Naming:** generic descriptions only — **no real brand or trademark names** (no Intel, AMD, Sony, Logitech, Kingston, MSI, DJI, Apple, Samsung, etc.). Technology class names are OK (`DDR4`, `NVMe`, `Wi-Fi 6`, `QLED`, `OLED`, `RTX` as product class).

## Category slugs (18 top-level)

| # | `category_slug` | `name_pt` |
|---|-----------------|-----------|
| 1 | `hardware` | Hardware |
| 2 | `peripherals` | Periféricos |
| 3 | `computers` | Computadores |
| 4 | `games_consoles` | Games & Consoles |
| 5 | `smartphones` | Smartphones |
| 6 | `monitors_displays` | Monitores & Displays |
| 7 | `tvs` | TVs |
| 8 | `audio` | Áudio |
| 9 | `projectors` | Projetores |
| 10 | `tablets_ereaders` | Tablets & E-readers |
| 11 | `cameras_drones` | Câmeras & Drones |
| 12 | `connectivity` | Conectividade |
| 13 | `power` | Energia |
| 14 | `smart_home` | Smart Home |
| 15 | `security` | Segurança |
| 16 | `gaming_space` | Espaço Gamer |
| 17 | `office` | Escritório |
| 18 | `automation_robotics` | Automação & Robótica |

## Store navigation (optional subcategories)

Subcategory rows in `product_categories` are **navigation only** — products always FK the **top-level** category. Subcategories may be seeded for future UI; generator does not require them on `products`.

## Products by category (generic names)

### 1. hardware

| Product |
|---------|
| Processador Ryzen 5 série 5000 |
| Processador Ryzen 7 série 7000 (cache 3D) |
| Processador Intel Core i5 14ª geração |
| Placa de vídeo RTX 4060 8GB |
| Placa de vídeo RX 7600 8GB |
| Memória RAM 16GB DDR4 |
| Memória RAM 32GB DDR5 |
| SSD NVMe 1TB |
| Fonte ATX 650W 80 Plus |
| Placa-mãe AM4 micro-ATX |

### 2. peripherals

| Product |
|---------|
| Teclado mecânico ABNT2 |
| Mouse gamer sem fio leve |
| Mouse gamer sensor 25K |
| Mouse ergonômico com fio |
| Headset gamer surround 7.1 |
| Headset sem fio dual-mode |
| Mousepad extended RGB |
| Microfone USB cardioid |
| Webcam Full HD 1080p |
| Controle gamer USB/sem fio |

### 3. computers

| Product |
|---------|
| PC Gamer Ryzen 5 + RTX 4060 |
| PC Gamer Ryzen 7 + RTX 4070 |
| PC Gamer Intel Core i5 |
| Desktop Intel Core i5 |
| Desktop Ryzen 5 |
| Mini PC Intel N100 |
| Mini PC Ryzen compacto |
| All-in-One 23,8" |
| Mini desktop compacto |
| Workstation profissional |

### 4. games_consoles

| Product |
|---------|
| Console de videogame Slim |
| Console de videogame Pro |
| Console digital compacto |
| Console premium 4K |
| Console portátil OLED |
| Console portátil nova geração |
| Controle ergonômico sem fio |
| Controle multiplataforma sem fio |
| Volante gamer com pedais |
| Headset para console |

### 5. smartphones

| Product |
|---------|
| Smartphone topo de linha 128GB |
| Smartphone econômico 128GB |
| Smartphone premium câmera 256GB |
| Smartphone ultra premium 512GB |
| Smartphone entrada dual chip |
| Smartphone intermediário 128GB |
| Smartphone intermediário câmera 64MP |
| Smartphone custo-benefício 128GB |
| Smartphone entrada 64GB |
| Smartphone 5G intermediário |

### 6. monitors_displays

| Product |
|---------|
| Monitor Gamer 24" 144Hz |
| Monitor Gamer 27" 165Hz |
| Monitor Gamer 32" QHD |
| Monitor Ultrawide 34" |
| Monitor 4K 27" |
| Monitor IPS 24" |
| Monitor USB-C |
| Monitor Curvo 27" |
| Monitor Profissional 32" |
| Monitor Smart 32" |

### 7. tvs

| Product |
|---------|
| Smart TV 32" HD |
| Smart TV 43" 4K |
| Smart TV 50" 4K |
| Smart TV 55" 4K |
| Smart TV 65" 4K |
| Smart TV QLED 55" |
| Smart TV QLED 65" |
| Smart TV OLED 55" |
| Smart TV OLED 65" |
| Smart TV 75" 4K |

### 8. audio

| Product |
|---------|
| Fone Bluetooth TWS |
| Headphone Bluetooth over-ear |
| Headset Gamer com microfone |
| Caixa de Som Bluetooth |
| Caixa de Som Portátil |
| Soundbar 2.1 |
| Microfone USB estúdio |
| Microfone Condensador |
| Speaker inteligente com assistente |
| Subwoofer passivo |

### 9. projectors

| Product |
|---------|
| Projetor Full HD |
| Projetor 4K |
| Mini Projetor Portátil |
| Projetor Gamer baixa latência |
| Projetor Home Theater |
| Projetor LED |
| Projetor com sistema smart |
| Projetor Wi-Fi |
| Tela para Projetor 120" |
| Suporte para Projetor teto |

### 10. tablets_ereaders

| Product |
|---------|
| Tablet premium 10" |
| Tablet intermediário 10" |
| Tablet profissional 11" |
| Tablet entrada 8" |
| Tablet premium com caneta |
| Tablet Android 10" |
| Tablet Android 10" básico |
| Tablet Android 12" |
| Leitor digital 6" |
| E-reader 6" iluminado |

### 11. cameras_drones

| Product |
|---------|
| Câmera Digital Compacta |
| Câmera DSLR entrada |
| Câmera Mirrorless |
| Action Camera 4K |
| Câmera 4K compacta |
| Drone compacto com câmera |
| Drone intermediário dual-câmera |
| Drone com câmera 4K |
| Câmera Vlog com flip |
| Câmera Instantânea |

### 12. connectivity

| Product |
|---------|
| Roteador Wi-Fi 6 |
| Roteador Wi-Fi 7 |
| Sistema Mesh Wi-Fi (kit) |
| Access Point empresarial |
| Switch Gigabit 8 Portas |
| Switch 24 Portas gerenciável |
| Adaptador USB Wi-Fi |
| Adaptador Bluetooth USB |
| Repetidor Wi-Fi |
| Placa de Rede PCIe Gigabit |

### 13. power

| Product |
|---------|
| Nobreak 600VA |
| Nobreak 1200VA |
| Nobreak Senoidal |
| Filtro de Linha 5 tomadas |
| Estabilizador 500VA |
| Protetor contra surtos |
| Fonte Universal notebook |
| Power Station portátil |
| Carregador USB-C 65W |
| Carregador GaN 100W |

### 14. smart_home

| Product |
|---------|
| Assistente de voz com alto-falante |
| Smart Speaker Wi-Fi |
| Lâmpada Inteligente RGB |
| Tomada Inteligente Wi-Fi |
| Interruptor Inteligente |
| Sensor de Movimento |
| Sensor de Porta/Janela |
| Hub Smart Home |
| Campainha Inteligente |
| Câmera Wi-Fi interna |

### 15. security

| Product |
|---------|
| Câmera IP Wi-Fi externa |
| Câmera PTZ motorizada |
| Câmera Dome fixa |
| Câmera Bullet externa |
| Kit CFTV 4 câmeras |
| DVR 8 canais |
| NVR 8 canais PoE |
| Fechadura Digital |
| Vídeo Porteiro Wi-Fi |
| Sensor de Presença |

### 16. gaming_space

| Product |
|---------|
| Cadeira Gamer reclinável |
| Mesa Gamer com mousepad |
| Suporte para Monitor articulado |
| Suporte para Headset |
| Suporte para Controle |
| Desk Mat XXL |
| Braço para Microfone |
| Suporte para Notebook |
| Iluminação RGB LED strip |
| Organizador de Cabos |

### 17. office

| Product |
|---------|
| Webcam Full HD |
| Webcam 4K |
| Impressora Multifuncional |
| Impressora Laser monocromática |
| Impressora Térmica |
| Scanner de mesa |
| Monitor Home Office 27" |
| Teclado Office silencioso |
| Mouse Ergonômico vertical |
| Hub USB-C 7 portas |

### 18. automation_robotics

| Product |
|---------|
| Robô Aspirador |
| Robô Educacional programável |
| Kit Arduino iniciante |
| Kit Raspberry Pi completo |
| Braço Robótico didático |
| Sensor Arduino kit |
| Motor de Passo |
| Kit Eletrônica básico |
| Placa de Desenvolvimento |
| Kit IoT Wi-Fi |

## SKU pattern

`TS-{CATEGORY_ABBR}-{SEQ:02}` — e.g. `TS-HW-01` … `TS-HW-10`.

## Warranty bands (default)

| Categories | `warranty_days` |
|------------|-----------------|
| computers, smartphones, tablets_ereaders, tvs, monitors_displays | 365 |
| hardware, games_consoles, cameras_drones, projectors | 180 |
| all others | 90 |

## Price generation

```python
# Deterministic per (seed, sku): uniform in category price_bands from company.yaml
price = rng.uniform_decimal(band["min"], band["max"], quantize="0.01")
```

Same `seed` + `sku` → same `unit_price` across runs.
