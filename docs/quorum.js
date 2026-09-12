/* Quorum site behaviour. Every piece here does real work:
   nothing animates for decoration, and the page is correct with JS disabled. */
(function () {
  "use strict";

  /* ---------- theme: system by default, remembered once chosen ----------
     A theme change is instant; never animated (hard rule 4). */
  var root = document.documentElement;
  var btn = document.getElementById("theme-toggle");
  var LABEL = { light: "Light", dark: "Dark", system: "Auto" };
  var stored = null;
  try { stored = localStorage.getItem("quorum-theme"); } catch (e) {}
  var apply = function (mode) {
    if (mode === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", mode);
    if (btn) {
      btn.textContent = LABEL[mode];
      btn.setAttribute("aria-label", "Theme: " + LABEL[mode] + ". Activate to change.");
    }
  };
  var current = stored === "light" || stored === "dark" ? stored : "system";
  apply(current);
  if (btn) {
    btn.addEventListener("click", function () {
      current = current === "system" ? "light" : (current === "light" ? "dark" : "system");
      apply(current);
      try {
        if (current === "system") localStorage.removeItem("quorum-theme");
        else localStorage.setItem("quorum-theme", current);
      } catch (e) {}
    });
  }

  /* ---------- the deletion test: one switch, and the mark follows it ---------- */
  var on = document.getElementById("pane-on"),
      off = document.getElementById("pane-off"),
      bOn = document.getElementById("btn-on"),
      bOff = document.getElementById("btn-off");
  if (on && off && bOn && bOff) {
    var marks = document.querySelectorAll("[data-mark]"),
        swOn = document.getElementById("sw-on"),
        swOff = document.getElementById("sw-off"),
        state = document.getElementById("term-state"),
        answer = document.getElementById("answer-n"),
        /* the number beside the switch is read off the terminal it points at, never typed in here */
        confirmedIn = function (pre) { var m = /confirmed (\d+)/.exec(pre.textContent); return m ? m[1] : ""; },
        /* the memory page keeps both panes in view; the switch then chooses which one is the record */
        keep = on.hasAttribute("data-keep");
    var show = function (memoryOn) {
      if (!keep) {
        on.hidden = !memoryOn;
        off.hidden = memoryOn;
      }
      if (swOn) swOn.hidden = !memoryOn;
      if (swOff) swOff.hidden = memoryOn;
      if (state) state.textContent = memoryOn ? "Memory on" : "Memory off";
      if (answer) answer.textContent = confirmedIn(memoryOn ? on : off);
      bOn.setAttribute("aria-pressed", String(memoryOn));
      bOff.setAttribute("aria-pressed", String(!memoryOn));
      document.body.setAttribute("data-memory", memoryOn ? "on" : "off");
      for (var i = 0; i < marks.length; i++) {
        marks[i].setAttribute("data-mark", memoryOn ? "agreed" : "void");
      }
    };
    bOn.addEventListener("click", function () { show(true); });
    bOff.addEventListener("click", function () { show(false); });
  }

  /* ---------- copy a command block ---------- */
  document.querySelectorAll("[data-copy]").forEach(function (pre) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy";
    btn.textContent = "Copy";
    btn.setAttribute("aria-label", "Copy these commands");
    btn.addEventListener("click", function () {
      var text = pre.innerText.replace(/^\$ /gm, "");
      var done = function (ok) {
        btn.textContent = ok ? "Copied" : "Press ⌘C";
        setTimeout(function () { btn.textContent = "Copy"; }, 1600);
      };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); });
      } else { done(false); }
    });
    pre.parentNode.insertBefore(btn, pre);
  });

  /* ---------- verify the published claim against Base, in this browser ---------- */
  var v = document.getElementById("verify");
  if (v) {
    var TX = v.getAttribute("data-tx"),
        EXPECT = v.getAttribute("data-digest").toLowerCase(),
        /* the same order quorum verify uses: the claim chain first, then every chain a claim has lived on */
        CHAINS = [
          { name: "Robinhood Chain", rpcs: ["https://rpc.mainnet.chain.robinhood.com"] },
          { name: "Base", rpcs: ["https://mainnet.base.org", "https://base-rpc.publicnode.com"] }
        ],
        vbtn = document.getElementById("verify-btn"),
        out = document.getElementById("verify-out"),
        status = document.getElementById("verify-status");

    var call = function (rpc, method, params) {
      return fetch(rpc, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: method, params: params })
      }).then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      }).then(function (j) {
        if (j.error) throw new Error(j.error.message || "RPC error");
        return j.result;
      });
    };
    var onChain = function (chain, method, params) {
      var p = Promise.reject(new Error("no rpc"));
      chain.rpcs.forEach(function (rpc) { p = p.catch(function () { return call(rpc, method, params); }); });
      return p;
    };
    /* find the transaction: only "not on this chain" moves on; a node that is down is reported, not skipped */
    var findTx = function (hash) {
      var p = Promise.resolve(null);
      CHAINS.forEach(function (chain) {
        p = p.then(function (found) {
          if (found) return found;
          return onChain(chain, "eth_getTransactionByHash", [hash]).then(function (tx) {
            return tx ? { chain: chain, tx: tx } : null;
          });
        });
      });
      return p.then(function (found) {
        if (!found) throw new Error("transaction not found on Robinhood Chain or Base");
        return found;
      });
    };
    var hexToAscii = function (hex) {
      var s = "";
      for (var i = 0; i < hex.length; i += 2) {
        var c = parseInt(hex.substr(i, 2), 16);
        if (c >= 32 && c < 127) s += String.fromCharCode(c); else break;
      }
      return s;
    };
    var set = function (id, text, cls) {
      var el = document.getElementById(id);
      if (!el) return;
      el.textContent = text;
      if (cls) el.className = cls;
    };

    vbtn.addEventListener("click", function () {
      vbtn.disabled = true;
      status.textContent = "Reading Robinhood Chain…";
      findTx(TX).then(function (found) {
        return onChain(found.chain, "eth_blockNumber", []).then(function (h) {
          return { tx: found.tx, chain: found.chain, head: parseInt(h, 16) };
        });
      }).then(function (res) {
        var tx = res.tx, head = res.head;
        set("v-chain", res.chain.name);
        var block = parseInt(tx.blockNumber, 16);
        var data = tx.input.slice(2);
        var prefix = hexToAscii(data);
        var version = prefix.indexOf("QUORUM2") === 0 ? 2 : (prefix.indexOf("QUORUM1") === 0 ? 1 : 0);
        if (!version) throw new Error("calldata carries no QUORUM prefix");
        var body = data.slice(14); // 7 ascii bytes
        var digest = "0x" + body.slice(0, 64);
        var burn = version === 2 ? "0x" + body.slice(64, 128) : null;

        out.hidden = false;
        set("v-prefix", "QUORUM" + version + (version === 1 ? " (published before the fee existed)" : ""));
        set("v-block", block.toLocaleString() + "  ·  " + (head - block).toLocaleString() + " confirmations");
        set("v-from", tx.from);
        set("v-selfaddr", tx.to && tx.to.toLowerCase() === tx.from.toLowerCase()
              ? "yes, the signer addressed it to itself" : "no");
        set("v-digest", digest);
        set("v-burn", burn ? burn : "none: a v1 claim carries no fee burn");
        var match = digest.toLowerCase() === EXPECT;
        set("v-match", match
              ? "matches the digest printed on this page"
              : "does NOT match the digest printed on this page", match ? "ok" : "bad");
        status.textContent = "Read from " + res.chain.name + " just now, in your browser. Nothing was sent anywhere.";
        vbtn.disabled = false;
        vbtn.textContent = "Read it again";
      }).catch(function (e) {
        status.textContent = "Could not read the claim from this browser (" + e.message +
          "). The facts above come from the transaction itself and are unchanged.";
        vbtn.disabled = false;
      });
    });
  }

  /* ---------- live token supply, read from Robinhood Chain ---------- */
  var sup = document.getElementById("supply"), supN = document.getElementById("supply-n");
  if (sup) {
    sup.textContent = "Reading the token contract…";
    fetch("https://rpc.mainnet.chain.robinhood.com", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0", id: 1, method: "eth_call",
        params: [{ to: sup.getAttribute("data-token"), data: "0x18160ddd" }, "latest"]
      })
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (!j.result) throw new Error("no result");
      var whole = BigInt(j.result) / (10n ** 18n);
      if (supN) {
        supN.textContent = whole.toLocaleString();
        sup.textContent = "QUORUM in existence, read from the chain just now";
      } else {
        sup.textContent = whole.toLocaleString() + " QUORUM in existence, read from the chain just now";
      }
    }).catch(function () {
      if (supN) supN.textContent = "";
      sup.textContent = "Supply is read from the token contract; this browser could not reach the chain.";
    });
  }

})();
