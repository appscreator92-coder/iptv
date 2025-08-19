#!/bin/bash
base_url="https://spoo.me/yBR2jV"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
MAX_JOBS=10
RETRY_COUNT=3
README="./readme.md"
STATUSLOG=$(mktemp)
PASSED=0
FAILED=0
EMPTY=0

get_status() {
    local url="$1"
    local channel="$2"
    local attempt response status_code

    [[ "$url" != http* ]] && return

    for attempt in $(seq 1 "$RETRY_COUNT"); do
        response=$(curl -sL -A "$UA" -o /dev/null --max-time 10 -w "%{http_code}" "$url" 2>&1)
        [[ "$response" =~ ^[0-9]+$ ]] && break
        sleep 1
    done

    if [[ ! "$response" =~ ^[0-9]+$ ]]; then
        if [[ "$response" == *"timed out"* ]]; then
            echo "| $channel | Connection timed out | \`$url\` |" >>"$STATUSLOG"
        else
            echo "| $channel | Curl error | \`$url\` |" >>"$STATUSLOG"
        fi
        echo "FAIL" >>"$STATUSLOG"
        return
    fi

    status_code="$response"

    case "$status_code" in
    200)
        if ! curl -sL -A "$UA" --max-time 5 "$url" | head -c 1 | grep -q '.'; then
            echo "| $channel | Empty body (404) | \`$url\` |" >>"$STATUSLOG"
            echo "EMPTY" >>"$STATUSLOG"
        else
            echo "PASS" >>"$STATUSLOG"
        fi
        ;;
    4* | 5*)
        echo "| $channel | HTTP Error ($status_code) | \`$url\` |" >>"$STATUSLOG"
        echo "FAIL" >>"$STATUSLOG"
        ;;
    *)
        if [[ "$status_code" == "000" ]]; then
            echo "| $channel | Connection timed out (000) | \`$url\` |" >>"$STATUSLOG"
        else
            echo "| $channel | Unknown status ($status_code) | \`$url\` |" >>"$STATUSLOG"
        fi
        echo "FAIL" >>"$STATUSLOG"
        ;;
    esac
}

check_links() {
    echo "Checking links from: $base_url"
    channel_num=0
    name=""
    jobs_running=0

    echo "| Channel | Error (Code) | Link |" >"$STATUSLOG"
    echo "| ------- | ------------ | ---- |" >>"$STATUSLOG"

    while IFS= read -r line; do
        line=$(echo "$line" | tr -d '\r\n')

        if [[ "$line" == \#EXTINF* ]]; then
            name=$(echo "$line" | sed -n 's/.*tvg-name="\([^"]*\)".*/\1/p')
            [[ -z "$name" ]] && name="Channel $channel_num"
        elif [[ "$line" =~ ^https?:// ]]; then
            while (($(jobs -r | wc -l) >= MAX_JOBS)); do sleep 0.2; done
            get_status "$line" "$name" &
            ((channel_num++))
        fi
    done < <(curl -sL -A "$UA" "$base_url")

    wait
    echo "Done."
}

write_readme() {
    local passed redirected empty failed
    passed=$(grep -c '^PASS$' "$STATUSLOG")
    empty=$(grep -c '^EMPTY$' "$STATUSLOG")
    failed=$(grep -c '^FAIL$' "$STATUSLOG")

    {
        echo "## Log @ $(date '+%Y-%m-%d %H:%M UTC')"
        echo
        echo "### ✅ Working Streams: $passed<br>➖ Empty Streams: $empty<br>❌ Dead Streams: $failed"
        echo

        if (($failed > 0 || $empty > 0)); then
            head -n 1 "$STATUSLOG"
            grep -v -e '^PASS$' -e '^FAIL$' -e '^EMPTY$' -e '^---' "$STATUSLOG" | grep -v '^| Channel' | sort -u
        fi

        echo "---"
        echo "#### M3U8 URL"
        printf "\`\`\`\nhttps://spoo.me/d9M3U8\n\`\`\`\n"
        echo "#### EPG URL"
        printf "\`\`\`\nhttps://spoo.me/d9EPG\n\`\`\`\n"
        echo "---"
        echo "#### Legal Disclaimer"
        echo "This repository lists publicly accessible IPTV streams as found on the internet at the time of checking."
        echo "No video or audio content is hosted in this repository. These links may point to copyrighted material owned by third parties;"
        echo "they are provided **solely for educational and research purposes.**"
        echo "The author does not endorse, promote, or encourage illegal streaming or copyright infringement."
        echo "End users are solely responsible for ensuring they comply with all applicable laws in their jurisdiction before using any link in this repository."
        echo "If you are a rights holder and wish for a link to be removed, please open an issue."

    } >"$README"
}

check_links
write_readme
rm "$STATUSLOG"
