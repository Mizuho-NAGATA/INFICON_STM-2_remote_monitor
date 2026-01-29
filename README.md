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
本システムは Docker を内部で使用していますが、簡単に使えるように **ワンクリック起動の bat ファイル** を用意しています。

### 2-1. Docker Desktop をインストール  
Windows で Docker を利用するために、Docker Desktop をインストールします。  
公式サイト：
<a href="https://www.docker.com/products/docker-desktop/" target="_blank">https://www.docker.com/products/docker-desktop/</a>

### 2-2. リポジトリを取得  
コマンドプロンプトで下記を実行。
```
git clone https://github.com/Mizuho-NAGATA/INFICON_STM-2_remote_monitor
```
次に下記を実行。
```
cd INFICON_STM-2_remote_monitor
```

### 2-3. **start_monitoring.bat をダブルクリックする**
## ▶ 起動
C:\Users\（ユーザー名）\INFICON_STM-2_remote_monitor\INFICON_STM-2_remote_monitor\start_monitoring.bat  
をダブルクリックして実行
- Docker Desktop が自動起動<br>  
- 完全起動まで自動待機<br>  
- InfluxDB / Grafana が自動起動<br>  
- Grafana が自動でブラウザで開く<br>  

## ■ 停止
C:\Users\（ユーザー名）\INFICON_STM-2_remote_monitor\INFICON_STM-2_remote_monitor\stop_monitoring.bat  
をダブルクリックして停止。

<p>
  <a href="https://github.com/Mizuho-NAGATA/INFICON_STM-2_remote_monitor/raw/main/stop_monitoring.bat">
    <img src="https://img.shields.io/badge/Stop%20Monitoring.bat-Download-red?style=for-the-badge">
  </a>
</p>

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
```INFICON_STM-2_remote_monitor/
├── start_monitoring.bat        ← 監視システムをワンクリックで起動（Docker自動起動・Grafana自動表示）
├── stop_monitoring.bat         ← 監視システムをワンクリックで停止
│
├── src/
│   ├── gui_app.py              ← STM-2 の .log を読み取り InfluxDB に送信する GUI アプリ
│   └── stm2_reader_core.py     ← ログ解析とデータ送信のコア処理（GUI から呼び出される）
│
├── docker-compose.yml          ← InfluxDB と Grafana を起動する設定ファイル（bat が内部で使用）
│
└── docker/
    └── grafana/
        └── provisioning/
            ├── dashboards/
            │   └── STM-2_dashboard.json   ← Grafana ダッシュボードの自動読み込み設定
            └── datasources/
                └── influxdb.yml               ← InfluxDB のデータソース設定（Grafana が自動で参照）
```

---
## 備考  
- InfluxDB は v1.x を使用（GUI のコードと互換性あり）  
- GUI は Windows 上で動作し、Docker とは独立  
- Docker 化により環境構築の手間が大幅に削減されます
