# INFICON STM‑2 Remote — Real‑time STM‑2 .log Monitoring (InfluxDB + Grafana) (UNOFFICIAL)
- INFICON STM-2 USB 薄膜蒸着レート/膜厚モニター の.logファイルを遠隔監視するためのシステム。
- **InfluxDB** と **Grafana** を用いてネットワーク越しにリアルタイムで可視化します。  
- このリポジトリには、すぐに利用できる Grafana ダッシュボード（JSON）が含まれています。
- System for remote monitoring of .log files from the INFICON STM-2 USB Thin Film Deposition Rate/Film Thickness Monitor.
- Visualizes data in real time over the network using InfluxDB and Grafana.
- This repository includes a ready-to-use Grafana dashboard (JSON).

![外部向け説明資料](https://github.com/user-attachments/assets/eb5fce0c-8dbf-4847-b3d2-5c2d21164ab5)  

## ✨ 特長

- STM-2 の膜厚・成膜レート・周波数をリアルタイム監視
- ネットワーク経由での多地点同時監視
- 目標厚さの80%を超えるとパネルが赤く点灯してお知らせします
- Real-time monitoring of STM-2 film thickness, deposition rate, and frequency
- Simultaneous multi-site monitoring via network
- Panel lights up red to notify when thickness exceeds 80% of target thickness
![keikoku](https://github.com/user-attachments/assets/13df291b-82ce-4b08-9643-8e03dbeeca35)

注意：このプログラムはINFICON社の公式なものではありません。  
本リポジトリの著者は商用サポートを提供するものではありません。ネットワーク構成やセキュリティ対策は各組織のポリシーに従って実施してください。  
本システムで使用する物性値について、正確性を保証するものではありません。利用により生じたいかなる結果についても、作者は責任を負いません。  
電子ビーム蒸着装置に取り付けられたSTM-2を想定して作成。  
Note: This program is not official INFICON.  
The author of this repository does not provide commercial support. Network configuration and security measures should be implemented in accordance with each organization's policies.  

## STM-2接続パソコンの準備：

### 🪟 Windows の場合
Windows Defender ファイアウォールに受信規則を追加してポート3000を開放する。  
固定IPアドレスを設定する。あらかじめネットワーク管理者に確認することをおすすめします。 

#### Pythonをインストール  
公式サイト： <a href="https://www.python.org/" target="blank">https://www.python.org/</a>  

コマンドプロンプトで下記のコマンドを実行して必要なライブラリをインストールする。  
```cmd
pip install influxdb customtkinter tkinterdnd2
```

または requirements.txt を使用：
```cmd
pip install -r requirements.txt
```

#### InfluxDBをインストール  
公式サイト： <a href="https://www.influxdata.com/" target="blank">https://www.influxdata.com/</a>     
STM-2 のログスクリプトとの互換性のため、InfluxDB v1.x を推奨します。  

#### Grafanaをインストール  
公式サイト： <a href="https://grafana.com/" target="_blank"> https://grafana.com/ </a>

"STM-2_dashboard.json" をインポートして各種設定を完了させる。  
- Grafana → Dashboards → Import  
- JSON Upload または JSON を貼り付け  
- Data source を InfluxDB に設定  

---

### 🍎 macOS の場合
ファイアウォール設定でポート3000を開放する。  
固定IPアドレスを設定する。あらかじめネットワーク管理者に確認することをおすすめします。

#### Pythonをインストール  
公式サイト： <a href="https://www.python.org/" target="blank">https://www.python.org/</a>  
または Homebrew を使用：
```bash
brew install python3
```

ターミナルで下記のコマンドを実行して必要なライブラリをインストールする。  
```bash
pip3 install influxdb customtkinter tkinterdnd2
```

または requirements.txt を使用：
```bash
pip3 install -r requirements.txt
```

#### InfluxDBをインストール  
Homebrew を使用してインストール：
```bash
brew install influxdb@1
brew services start influxdb@1
```

または公式サイト： <a href="https://www.influxdata.com/" target="blank">https://www.influxdata.com/</a>  

#### Grafanaをインストール  
Homebrew を使用してインストール：
```bash
brew install grafana
brew services start grafana
```

または公式サイト： <a href="https://grafana.com/" target="_blank"> https://grafana.com/ </a>

"STM-2_dashboard.json" をインポートして各種設定を完了させる。  
- Grafana → Dashboards → Import  
- JSON Upload または JSON を貼り付け  
- Data source を InfluxDB に設定  

---

### 🐧 Linux の場合
ファイアウォール設定（iptables または firewalld）でポート3000を開放する。  
固定IPアドレスを設定する。あらかじめネットワーク管理者に確認することをおすすめします。

#### Pythonをインストール  
多くの Linux ディストリビューションには Python3 がプリインストールされています。  
未インストールの場合：
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# Fedora/RHEL/CentOS
sudo dnf install python3 python3-pip
```

ターミナルで下記のコマンドを実行して必要なライブラリをインストールする。  
```bash
pip3 install influxdb customtkinter tkinterdnd2
```

または requirements.txt を使用：
```bash
pip3 install -r requirements.txt
```

**注意**: 日本語フォントが必要です。未インストールの場合：
```bash
# Ubuntu/Debian
sudo apt install fonts-noto-cjk

# Fedora/RHEL/CentOS
sudo dnf install google-noto-sans-cjk-jp-fonts
```

#### InfluxDBをインストール  
公式サイトの手順に従ってインストール： <a href="https://www.influxdata.com/" target="blank">https://www.influxdata.com/</a>  

Ubuntu/Debian の場合：
```bash
wget https://dl.influxdata.com/influxdb/releases/influxdb_1.8.10_amd64.deb
sudo dpkg -i influxdb_1.8.10_amd64.deb
sudo systemctl start influxdb
sudo systemctl enable influxdb
```

#### Grafanaをインストール  
公式サイトの手順に従ってインストール： <a href="https://grafana.com/" target="_blank"> https://grafana.com/ </a>

Ubuntu/Debian の場合：
```bash
sudo apt-get install -y software-properties-common
sudo mkdir -p /etc/apt/keyrings/
wget -q -O - https://packages.grafana.com/gpg.key | gpg --dearmor | sudo tee /etc/apt/keyrings/grafana.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

"STM-2_dashboard.json" をインポートして各種設定を完了させる。  
- Grafana → Dashboards → Import  
- JSON Upload または JSON を貼り付け  
- Data source を InfluxDB に設定  

---
## 動作手順：
## 🖥️ **STM‑2 接続パソコンで行う作業**

### 1. **STM‑2専用ソフトウェア（INFICON）**
- INFICON公式 STM‑2 ソフトを起動  
- 必要な設定を行い、**記録 Start**

### 2. **InfluxDB の起動**
- InfluxDB のフォルダへ移動  
- Shift＋右クリック → **「ここでコマンドウィンドウを開く」**  
- コマンドプロンプトで  
  ```
  .\influxd
  ```  
  を実行し、InfluxDB を起動

### 3. **Python GUI（蒸着モニタリングアプリ）**
- Python コードを実行して GUI を起動
- 目標厚さ（nm）を入力  
- 蒸着材料を選択 → **密度・Z‑ratio が自動入力**  
- 「参照」ボタンから **STM‑2 のログファイル（現在記録中のもの）** を選択  
- GUI が InfluxDB にデータを書き込み始める
![GUI](https://github.com/user-attachments/assets/0c668087-c73f-4ab3-9ee0-d0cd39099132)


---

## 💻 **クライアントPC（遠隔監視側）で行う作業**

### 1. **Grafana へアクセス**
- Webブラウザを開く  
- STM‑2接続PCの固定IPアドレスを指定してアクセス  
  ```
  http://（STM‑2接続PCの固定IP）:3000
  ```
- Grafana ダッシュボードでリアルタイム監視

---

## 著者  
- Copyright (c) 2026 NAGATA Mizuho, 永田 みず穂 - Institute of Laser Engineering, The University of Osaka
---

## ライセンス License
- このプロジェクトはMITライセンスの下で公開されています。ライセンスの全文については、[LICENSE](https://github.com/Mizuho-NAGATA/INFICON_STM-2_remote_monitor/blob/main/LICENSE) をご覧ください。  
- This project is released under the MIT License. For the full text of the license, please see the LICENSE file.
---

## 謝辞
- 本開発は文部科学省先端研究基盤共用促進事業（先端研究設備プラットフォームプログラム） JPMXS0450300021である[パワーレーザーDXプラットフォーム](https://powerlaser.jp/)で共用された機器を利用した成果です。
- This work was the result of using research equipment shared by the [Power Laser DX Platform(https://powerlaser.jp/), which is MEXT Project for promoting public utilization of advanced research infrastructure（Program for advanced research equipment platforms）Grant Number JPMXS0450300021.
