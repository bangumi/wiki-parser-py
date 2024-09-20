from bgm_tv_wiki import parse


raw = """{{Infobox animanga/TVAnime
|中文名= 【我推的孩子】 第二季
|别名={
[[Oshi no Ko] 2nd Season]
["Oshi no Ko" 2]
}
|话数= 13
|放送开始= 2024年7月3日
|放送星期= 星期三
|官方网站= https://ichigoproduction.com/
|播放电视台= TOKYO MX
|其他电视台= BS日テレ / サンテレビ / KBS京都 / メ～テレ / HTB北海道テレビ / ＲＫＢ毎日放送 / テレビ新広島 / ミヤギテレビ / テレビ静岡 / 新潟放送 / テレビ山梨 / テレビユー福島 / あいテレビ / 長崎放送 / IBC岩手放送 / チューリップテレビ / 北陸放送 / 福井テレビ / テレビユー山形 / 琉球放送 / 日本海テレビ / 鹿児島放送 / AT-X
|播放结束=
|其他=
|Copyright= ©赤坂アカ×横槍メンゴ／集英社・【推しの子】製作委員会
|原作= 赤坂アカ×横槍メンゴ（集英社「週刊ヤングジャンプ」連載）
|导演= 平牧大輔
|人物设定= 平山寛菜；副人设：澤井駿、渡部里美、横山穂乃花
|主动画师= 早川麻美、水野公彰、室賀彩花；动作动画师：あもーじー（武田駿）
|OP・ED 分镜= 竹下良平（OP）、中山直哉（ED）
|主题歌编曲= Giga(ギガP)（OP） / 羊文学（ED）
|主题歌作曲= Tatsuya Kitani(キタニタツヤ)（OP） / 塩塚モエカ（ED）
|主题歌作词= Tatsuya Kitani(キタニタツヤ)（OP） / 塩塚モエカ（ED）
|主题歌演出= GEMN（OP） / 羊文学（ED）
|製作= 【推しの子】製作委員会（KADOKAWA、集英社、動画工房、CyberAgent）
|企画= 菊池剛、工藤大丈、大好誠
|制片人= 吉岡拓也、山下愼平、岡川広樹、鎌田肇、青村陽介
|别名={
[[Oshi no Ko] 2nd Season]
["Oshi no Ko" 2]
["Oshi no Ko" 2]
["Oshi no Ko" 2]
["Oshi no Ko" 2]
["Oshi no Ko" 2]
["Oshi no Ko" 2]
["Oshi no Ko" 2]
["Oshi no Ko" 2]
["Oshi no Ko" 2]
["Oshi no Ko" 2]
["Oshi no Ko" 2]
}
|执行制片人= 田中翔、薄井勝太郎、石黒竜、椛嶋麻菜美
|原作协力= 増澤吉和、大沢太郎、酒井浩希
|协力= 根岸弦輝、笠原周造、清原誠巳、中山卓也、石澤紀子、尾形光広、井上智代、神原葉月
|音乐制作= KADOKAWA
|音乐制作人= 水鳥智栄子
|动作作画监督= あもーじー（武田駿）
}}"""


def test_my_stuff_different_arg(benchmark):
    benchmark(parse, raw)
