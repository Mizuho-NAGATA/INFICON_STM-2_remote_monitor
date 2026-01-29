# INFICON_STM-2_remote_monitor
- INFICON STM-2 USB 薄膜蒸着レート/膜厚モニター の.logファイルを遠隔監視するためのシステム。（INFICON非公式）  
- **InfluxDB** と **Grafana** を用いてリアルタイムに可視化します。  
 
![外部向け説明資料](https://github.com/user-attachments/assets/eb5fce0c-8dbf-4847-b3d2-5c2d21164ab5)
**注意：このプログラムはINFICON社の公式なものではありません。**  
**Note: This program is not official INFICON.**  

本システムで使用する物性値について、正確性を保証するものではありません。利用により生じたいかなる結果についても、作者は責任を負いません。  
電子ビーム蒸着装置に取り付けられたSTM-2を想定して作成。  

## ✨ 特長

- STM-2 の膜厚・成膜レート・周波数をリアルタイム監視
- 目標膜厚の 80% を超えた際に自動アラート
- Docker により InfluxDB と Grafana の環境構築が不要  

---
## 🖥️ 1. STM-2 接続パソコンの準備：
Windowsマシンを想定しています。  

### 1-1. ファイアウォール設定
- Windows Defender ファイアウォールに受信規則を追加してポート3000を開放する（Grafana用）。  
- 固定IPアドレスを設定する（遠隔監視用）。あらかじめネットワーク管理者に確認することをおすすめします。  

### 1-2. Python のインストール
Pythonをインストール。  
コマンドプロンプトで下記の三つのコマンドを実行して必要なライブラリをインストールする。  

pip install influxdb  
pip install customtkinter  
pip install tkinterdnd2  

### 1-3. Git for Windows をインストール
- 公式サイト:
<a href="https://git-scm.com/download/win" target="_blank" rel="noopener">https://git-scm.com/download/win</a>
- インストーラーを実行  
→ 「Next」を押していくだけで OK  
→ 特に設定を変える必要はありません  
→ “Git Bash Here” が追加されます  

### 1-4. STM-2専用ソフトウェア
INFICON公式STM-2専用ソフトウェアを起動。必要な設定をして記録 start。

---
## 🐳 2. 監視システムの起動方法
### 2-1. Docker Desktop をインストール  
Windows で Docker を利用するために、Docker Desktop をインストールします。  
公式サイト：
<a href="https://www.docker.com/products/docker-desktop/" target="_blank">https://www.docker.com/products/docker-desktop/</a>

### 2-2. リポジトリを取得  
```
git clone ...
cd INFICON_STM-2_remote_monitor
```

### 2-3. **start_monitoring.bat をダブルクリックするだけ**  
- Docker Desktop が自動起動  
- 完全起動まで自動待機  
- InfluxDB / Grafana が自動起動  
- Grafana が自動でブラウザで開く  
- ログが自動表示  
- エラーは logs/error_*.txt に保存  

### 2-3. 停止したいとき  
→ stop_monitoring.bat をダブルクリック

---

## 🖱️ 3. GUI アプリの使い方
GUI は Docker に入れず、Windows 上で動かします。  
コマンドプロンプトで下記を実行。

```bash
python src/gui_app.py
```

### GUI の操作  
- 目標厚さを nm で入力  
- 材料を選択すると密度と Z-ratio が自動入力  
- 「参照」ボタンで STM-2 の `.log` を選択  
- ログ監視が開始され、InfluxDB（Docker 内）に送信されます

---

### 📊 4. Grafana による遠隔監視
遠隔監視したいパソコンのwebブラウザを開き、下記URLを開く。  
http://（STM-2接続パソコンの固定IPアドレス）:3000  
- Grafana が表示されます  
- ダッシュボードは自動ロード済み  
- Data source は InfluxDB に設定済み
- 
---
## 📁 5. ディレクトリ構成
```
INFICON_STM-2_remote_monitor/
├── src/
│   ├── gui_app.py
│   └── stm2_reader_core.py
├── docker-compose.yml
└── docker/
    └── grafana/
        └── provisioning/
            ├── dashboards/
            │   └── STM-2-1769471897840.json
            └── datasources/
                └── influxdb.yml
```

---
## 備考  
- InfluxDB は v1.x を使用（GUI のコードと互換性あり）  
- GUI は Windows 上で動作し、Docker とは独立  
- Docker 化により環境構築の手間が大幅に削減されます
