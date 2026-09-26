/* MallHaul page controller: shared chrome + per-page renderers.
   Vanilla JS only. All data comes from the FastAPI backend. */
const I = {
  bag:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M6 7h12l1 13H5L6 7z"/><path d="M9 7a3 3 0 0 1 6 0"/></svg>',
  home:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="17" height="17"><path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/></svg>',
  mall:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="17" height="17"><path d="M4 9h16v11H4z"/><path d="M4 9l2-5h12l2 5"/><path d="M10 20v-6h4v6"/></svg>',
  play:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="17" height="17"><path d="M7 5l12 7-12 7z"/></svg>',
  box:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="17" height="17"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z"/><path d="M4 7.5l8 4.5 8-4.5"/><path d="M12 12v9"/></svg>',
  cart:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="17" height="17"><circle cx="9" cy="20" r="1.6"/><circle cx="18" cy="20" r="1.6"/><path d="M3 4h2l2.5 12h11L21 8H6"/></svg>',
  pin:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M12 21s-7-6-7-11a7 7 0 0 1 14 0c0 5-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>',
  qr:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><path d="M14 14h3v3h-3z"/></svg>',
  wallet:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><rect x="3" y="6" width="18" height="13" rx="2"/><path d="M16 12h3"/></svg>',
  truck:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><rect x="2" y="7" width="12" height="9"/><path d="M14 10h4l3 3v3h-7"/><circle cx="7" cy="18" r="1.6"/><circle cx="17" cy="18" r="1.6"/></svg>',
  check:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" width="16" height="16"><path d="M4 12l5 5L20 7"/></svg>',
  clock:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>',
  chev:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M9 5l7 7-7 7"/></svg>',
  trash:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="17" height="17"><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>',
  search:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>',
  store:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M4 9h16v11H4z"/><path d="M4 9l2-5h12l2 5"/></svg>',
};
const STAGES = ["Paid", "Packing", "Out for delivery", "Delivered"];
const NAV = {home:"Home", malls:"Malls", mall:"Malls", demo:"Demo",
             orders:"Orders", order:"Orders", cart:"Cart"};

function hue(s){let h=0;for(const c of s)h=(h*31+c.charCodeAt(0))%360;return h;}
function photo(url, alt, overlay){
  const h = hue(alt || "MH");
  const g = "linear-gradient(135deg,hsl("+h+",32%,34%),hsl("+((h+40)%360)+",40%,22%))";
  const init = '<div class="ph-init">'+esc((alt||"MH").slice(0,2).toUpperCase())+"</div>";
  const img = url ? '<img src="'+esc(url)+'" alt="'+esc(alt)+'" loading="lazy" onerror="this.remove()">' : "";
  return '<div class="photo" style="background:'+g+'">'+init+img+(overlay||"")+"</div>";
}
function thumb(name){
  const h = hue(name||"?");
  return '<div class="thumb" style="background:linear-gradient(135deg,hsl('+h+',30%,35%),hsl('+((h+40)%360)+',35%,22%))">'+esc((name||"?").slice(0,2).toUpperCase())+"</div>";
}
function header(activePage, me){
  const links = [["index.html","Home",I.home],["malls.html","Malls",I.mall],
    ["demo.html","Demo",I.play],["orders.html","Orders",I.box],
    ["cart.html","Cart",I.cart]];
  const count = me ? me.cart_items : 0;
  const auth = me
    ? '<span class="nav-link" title="'+esc(me.email)+'">Hi, '+esc(me.first_name)+"</span>"+
      '<button class="nav-link" onclick="API.post(\'/api/auth/logout\').then(()=>location.href=\'index.html\')">Sign out</button>'
    : '<a class="nav-link" href="login.html">Sign in</a>';
  document.getElementById("site-header").innerHTML =
    '<div class="nav"><a class="brand" href="index.html"><span class="brand-mark">'+I.bag+
    '</span><span><div class="brand-name">MallHaul</div><div class="brand-tag">One cart &middot; Many stores</div></span></a>'+
    '<nav class="nav-links">'+links.map(([href,label,icon]) =>
      '<a class="nav-link'+(activePage===label?" active":"")+'" href="'+href+'">'+icon+label+
      (label==="Cart"&&count?' <span class="badge">'+count+"</span>":"")+"</a>").join("")+auth+"</nav></div>";
}
function footer(){
  const f = document.getElementById("site-footer");
  if (f) f.innerHTML = "MallHaul &middot; Multi-store cart, wallet split &amp; QR consolidation &middot; <a href='security.html' style='text-decoration:underline'>Security &amp; SSDLC</a>";
}
async function getMe(){ try { return await API.get("/api/auth/me"); } catch(e){ return null; } }
function requireAuth(next){ location.href = "login.html?next="+encodeURIComponent(next||"index.html"); }
function trackerHTML(stage){
  const icons = [I.check, I.box, I.truck, I.check];
  let html = '<div class="tracker">';
  STAGES.forEach((label,i)=>{
    const done = i <= stage;
    html += '<div class="t-step'+(done?" done":"")+'"><div class="t-dot">'+(done?icons[i]:"")+"</div><span>"+label+"</span></div>";
    if (i < STAGES.length-1) html += '<div class="t-line'+(i<stage?" done":"")+'"></div>';
  });
  return html+"</div>";
}
function headerInit(me){ header(NAV[document.body.dataset.page]||"", me); }

const PAGES = {
  async home(){
    const me = await getMe(); headerInit(me);
    document.getElementById("main").innerHTML =
      '<div class="hero"><div class="kicker">'+I.mall+" MALLHAUL</div>"+
      "<h1>Shop every store.<br>One cart, one delivery.</h1>"+
      "<p>Create an account, browse your favourite malls, and add items from different stores into one trolley &mdash; paid into a single wallet and delivered together.</p>"+
      '<div class="actions"><a class="btn light" href="malls.html">Browse malls &rarr;</a><a class="btn light" href="orders.html">'+I.bag+" My orders</a></div></div>"+
      '<div class="section"><h2>How it works</h2><div class="sub">From sign-up to doorstep in four steps.</div><div class="steps">'+
      [["01","Create your account","Sign up and add your delivery details once."],
       ["02","Pick a mall","Browse or search malls, then enter the one you want."],
       ["03","Shop the stores","Search stores inside the mall and add items to one cart."],
       ["04","Pay &amp; track","Wallet splits per store, QR consolidates, live tracking."]]
      .map(s=>'<div class="step"><div class="num">'+s[0]+"</div><h3>"+s[1]+"</h3><p>"+s[2]+"</p></div>").join("")+"</div></div>"+
      '<div class="section"><h2>Everything in one haul</h2><div class="sub">A complete mall-to-doorstep experience.</div><div class="features">'+
      [[I.cart,"One unified cart","Items from every store in a mall, grouped and totaled per store"],
       [I.wallet,"Wallet split payments","Pay once into the mall wallet &mdash; we split and route per store"],
       [I.qr,"QR consolidation","Master QR links every store package into one shipment"],
       [I.truck,"Live delivery tracking","ETA with distance, status history, notifications"]]
      .map(f=>'<div class="feature"><div class="icon">'+f[0]+"</div><h3>"+f[1]+"</h3><p>"+f[2]+"</p></div>").join("")+"</div></div>"+
      '<div class="cta"><h2>Ready to start shopping?</h2><p>Pick a mall, search its stores, and fill one trolley.</p><a class="btn" href="malls.html">Browse malls &rarr;</a></div>';
  },

  async malls(){
    const me = await getMe(); headerInit(me);
    const main = document.getElementById("main");
    main.innerHTML = '<div class="kicker-sm">'+I.mall+" BROWSE MALLS</div>"+
      '<h1 class="page">Find your mall</h1><p class="page-sub">Search by name or city, then step inside to shop its stores.</p>'+
      '<div class="search" style="margin-top:24px">'+I.search+'<input id="q" placeholder="Search malls or cities"></div>'+
      '<div class="grid malls" id="list" style="margin-top:26px"></div>';
    const load = async () => {
      const q = document.getElementById("q").value.trim();
      const malls = await API.get("/api/malls"+(q?"?q="+encodeURIComponent(q):""));
      document.getElementById("list").innerHTML = malls.length ? malls.map(m =>
        '<a class="card mall-card" href="mall.html?id='+m._id+'">'+
        photo(m.image_url, m.name, '<div class="scrim"></div><div class="label"><h3>'+esc(m.name)+'</h3><div class="loc">'+I.pin+" "+esc(m.address.city+", "+m.address.province)+"</div></div>")+
        '<div class="body"><div><p>'+esc(m.description||"")+'</p><div class="meta">'+m.store_count+" stores</div></div>"+
        '<span class="chev">'+I.chev+"</span></div></a>").join("")
        : '<div class="empty">No malls match that search.</div>';
    };
    let t; document.getElementById("q").addEventListener("input",()=>{clearTimeout(t);t=setTimeout(load,250);});
    await load();
  },

  async mall(){
    const me = await getMe(); headerInit(me);
    const id = new URLSearchParams(location.search).get("id");
    const main = document.getElementById("main");
    let mall;
    try { mall = await API.get("/api/malls/"+id); }
    catch(e){ main.innerHTML = '<div class="empty">Mall not found.</div>'; return; }
    main.innerHTML = '<a class="back" href="malls.html">&lsaquo; Back to malls</a>'+
      '<div class="mall-hero">'+photo(mall.image_url, mall.name, '<div class="scrim"></div>')+
      '<div class="inner"><div class="loc">'+I.pin+" "+esc(mall.address.city+", "+mall.address.province)+"</div>"+
      "<h1>"+esc(mall.name)+"</h1><p>"+esc(mall.description||"")+'</p><div class="count">'+mall.stores.length+" stores open for delivery</div></div></div>"+
      '<div class="search" style="margin-top:24px">'+I.search+'<input id="sq" placeholder="Search stores in '+esc(mall.name)+'"></div>'+
      '<div class="chips" id="chips"></div><div class="grid stores" id="list"></div><div id="panel"></div>';
    const cats = ["All", ...new Set(mall.stores.map(s=>s.category_name))];
    let activeCat = "All";
    const render = () => {
      const q = document.getElementById("sq").value.trim().toLowerCase();
      const list = mall.stores.filter(s =>
        (activeCat==="All"||s.category_name===activeCat) && (!q||s.name.toLowerCase().includes(q)));
      document.getElementById("list").innerHTML = list.map(s =>
        '<div class="card store-card" data-id="'+s._id+'" data-name="'+esc(s.name)+'">'+
        photo(s.image_url, s.name)+
        '<div class="body"><div><h3>'+esc(s.name)+'</h3><div class="cat">'+esc(s.category_name)+" &middot; "+s.product_count+" items</div></div>"+
        '<span class="chev">'+I.chev+"</span></div></div>").join("") || '<div class="empty">No stores match.</div>';
      document.querySelectorAll(".store-card").forEach(el =>
        el.addEventListener("click",()=>openStore(el.dataset.id, el.dataset.name)));
    };
    document.getElementById("chips").innerHTML = cats.map(c =>
      '<button class="chip'+(c==="All"?" on":"")+'" data-c="'+esc(c)+'">'+esc(c)+"</button>").join("");
    document.querySelectorAll(".chip").forEach(ch => ch.addEventListener("click",()=>{
      activeCat = ch.dataset.c;
      document.querySelectorAll(".chip").forEach(x=>x.classList.toggle("on",x===ch));
      render();
    }));
    document.getElementById("sq").addEventListener("input", render);
    const openStore = async (sid, sname) => {
      const data = await API.get("/api/stores/"+sid+"/products");
      document.getElementById("panel").innerHTML =
        '<div class="card store-panel"><h3 style="margin-bottom:8px">'+esc(sname)+"</h3>"+
        (data.products.length ? data.products.map(p =>
          '<div class="prod-row">'+thumb(p.name)+
          '<div class="info"><b>'+esc(p.name)+"</b><span>"+(p.available>0 ? p.available+" in stock" : "Out of stock")+"</span></div>"+
          '<div class="price">'+money(p.pricing.selling_price)+"</div>"+
          '<button class="add-btn" data-p="'+p._id+'" '+(p.available>0?"":"disabled")+">Add</button></div>").join("")
          : '<div class="empty">No products yet.</div>')+"</div>";
      document.querySelectorAll(".add-btn").forEach(b => b.addEventListener("click", async ()=>{
        const m2 = await getMe();
        if (!m2) return requireAuth("mall.html?id="+id);
        try {
          await API.post("/api/cart/items",{product_id:b.dataset.p,quantity:1});
          toast("Added to trolley"); headerInit(await getMe());
        } catch(e) {
          if (e.code==="MALL_CONFLICT" && confirm(e.message+"\n\nClear the current trolley?")){
            await API.del("/api/cart");
            try { await API.post("/api/cart/items",{product_id:b.dataset.p,quantity:1}); toast("Added to trolley"); } catch(e2){ toast(e2.message); }
          } else toast(e.message);
        }
      }));
      document.getElementById("panel").scrollIntoView({behavior:"smooth"});
    };
    render();
  },

  async cart(){
    const me = await getMe(); headerInit(me);
    if (!me) return requireAuth("cart.html");
    const main = document.getElementById("main");
    const cart = await API.get("/api/cart");
    if (!cart.items || !cart.items.length){
      main.innerHTML = '<h1 class="page">Your trolley</h1><div class="empty">Your trolley is empty.<br><br><a class="btn" href="malls.html">Browse malls</a></div>';
      return;
    }
    const groups = {};
    cart.items.forEach(i => (groups[i.store_name] = groups[i.store_name]||[]).push(i));
    main.innerHTML = '<h1 class="page">Your trolley</h1>'+
      '<p class="page-sub">'+cart.items.length+" items from "+Object.keys(groups).length+" stores</p>"+
      '<div class="trolley-layout" style="margin-top:24px"><div>'+
      Object.entries(groups).map(([sname, items]) => {
        const sub = items.reduce((a,i)=>a+i.unit_price*i.quantity,0);
        return '<div class="card store-group"><div class="head">'+I.store+"<b>"+esc(sname)+"</b><span class=\"amt\">"+money(sub)+"</span></div>"+
          items.map(i => '<div class="item-row">'+thumb(i.product_name_snapshot)+
            '<div class="info"><b>'+esc(i.product_name_snapshot)+'</b><div class="each">'+money(i.unit_price)+" each</div></div>"+
            '<div class="stepper"><button data-a="dec" data-i="'+i._id+'">&minus;</button><span class="q">'+i.quantity+'</span><button data-a="inc" data-i="'+i._id+'">+</button></div>'+
            '<div class="line">'+money(i.unit_price*i.quantity)+'</div><button class="trash" data-a="del" data-i="'+i._id+'">'+I.trash+"</button></div>").join("")+"</div>";
      }).join("")+"</div>"+
      '<div class="card summary"><h3>Order summary</h3>'+
      '<div class="sumrow"><span>Subtotal ('+cart.items.length+" items)</span><b>"+money(cart.subtotal)+"</b></div>"+
      '<div class="sumrow"><span>Base delivery</span><b>'+money(cart.delivery_fee)+"</b></div>"+
      '<div class="note">+ door-to-door option at checkout</div>'+
      '<div class="sumrow total"><span>Estimated total</span><b>'+money(cart.total)+"</b></div>"+
      '<a class="btn wide" href="checkout.html">Pay with wallet &rarr;</a>'+
      '<a class="center-link" href="malls.html">Continue shopping</a></div></div>';
    main.querySelectorAll("[data-a]").forEach(b => b.addEventListener("click", async ()=>{
      const item = cart.items.find(i=>i._id===b.dataset.i);
      const qty = b.dataset.a==="inc" ? item.quantity+1 : b.dataset.a==="dec" ? item.quantity-1 : 0;
      try { await (b.dataset.a==="del" ? API.del("/api/cart/items/"+b.dataset.i)
            : API.patch("/api/cart/items/"+b.dataset.i,{quantity:qty})); PAGES.cart(); }
      catch(e){ toast(e.message); }
    }));
  },

  async checkout(){
    const me = await getMe(); headerInit(me);
    if (!me) return requireAuth("checkout.html");
    const main = document.getElementById("main");
    const cart = await API.get("/api/cart");
    if (!cart.items || !cart.items.length){ main.innerHTML = "<div class='empty'>Nothing to check out. <a href='malls.html' style='text-decoration:underline'>Browse malls</a></div>"; return; }
    let option = "BASE";
    const renderSummary = () => {
      const fee = option==="BASE" ? 35 : 55;
      document.getElementById("sum-fee").textContent = money(fee);
      document.getElementById("sum-total").textContent = money(Number(cart.subtotal)+fee);
      document.getElementById("fee-note").textContent = option==="BASE"
        ? "Consolidated at the mall hub, then delivered" : "Door-to-door premium delivery";
    };
    main.innerHTML = '<h1 class="page">Checkout</h1><p class="page-sub">One payment &mdash; we split it per store behind the scenes.</p>'+
      '<div class="trolley-layout" style="margin-top:24px"><div class="card panel">'+
      "<h2>Delivery address</h2><p class='sub'>Where should we bring your haul?</p>"+
      '<div class="field"><label>Street address</label><input id="a1" placeholder="e.g. 22 Palm Boulevard"></div>'+
      '<div class="field"><label>City</label><input id="city" value="Umhlanga"></div>'+
      '<div class="field"><label>Province</label><input id="prov" value="KwaZulu-Natal"></div>'+
      '<div class="field"><label>Postal code</label><input id="pc" value="4319"></div>'+
      "<h2 style='margin-top:10px'>Delivery option</h2>"+
      '<label class="radio-row on" data-o="BASE"><input type="radio" name="opt" checked><div><b>Base delivery &mdash; '+money(35)+"</b><span>Consolidated hub dispatch</span></div></label>"+
      '<label class="radio-row" data-o="DOOR_TO_DOOR"><input type="radio" name="opt"><div><b>Door-to-door &mdash; '+money(55)+"</b><span>Priority direct dispatch</span></div></label>"+
      '<label style="display:flex;gap:8px;align-items:center;font-size:13px;margin-top:6px"><input type="checkbox" id="save"> Save this address</label></div>'+
      '<div class="card summary"><h3>Order summary</h3>'+
      '<div class="sumrow"><span>Subtotal</span><b>'+money(cart.subtotal)+"</b></div>"+
      '<div class="sumrow"><span>Delivery</span><b id="sum-fee">'+money(35)+"</b></div>"+
      '<div class="note" id="fee-note">Consolidated at the mall hub, then delivered</div>'+
      '<div class="sumrow total"><span>Total</span><b id="sum-total">'+money(Number(cart.subtotal)+35)+"</b></div>"+
      '<button class="btn wide" id="pay">Pay with wallet &rarr;</button>'+
      '<button class="btn ghost wide" id="topup" style="margin-top:10px">Top up wallet R500 (demo)</button>'+
      '<a class="center-link" href="cart.html">Back to trolley</a>'+
      '<div class="note" style="margin-top:12px">Wallet balance: <b id="bal">'+money(me.wallet_balance)+"</b></div></div></div>";
    renderSummary();
    main.querySelectorAll(".radio-row").forEach(r => r.addEventListener("click",()=>{
      option = r.dataset.o;
      main.querySelectorAll(".radio-row").forEach(x=>x.classList.toggle("on",x===r));
      r.querySelector("input").checked = true; renderSummary();
    }));
    document.getElementById("topup").addEventListener("click", async ()=>{
      try { const r = await API.post("/api/wallet/topup",{amount:500});
        document.getElementById("bal").textContent = money(r.balance); toast("Wallet topped up"); }
      catch(e){ toast(e.message); }
    });
    document.getElementById("pay").addEventListener("click", async ()=>{
      const body = {
        address: {
          address_line_1: document.getElementById("a1").value.trim(),
          city: document.getElementById("city").value.trim(),
          province: document.getElementById("prov").value.trim(),
          postal_code: document.getElementById("pc").value.trim()||null,
        },
        delivery_option: option,
        save_address: document.getElementById("save").checked,
        idempotency_key: idem(),
      };
      if (!body.address.address_line_1) return toast("Enter a street address");
      try { const r = await API.post("/api/checkout", body);
        location.href = "order.html?id="+r.order_id; }
      catch(e){ toast(e.message); }
    });
  },

  async orders(){
    const me = await getMe(); headerInit(me);
    if (!me) return requireAuth("orders.html");
    const main = document.getElementById("main");
    main.innerHTML = '<h1 class="page">Your orders</h1><p class="page-sub">Track delivery status and view receipts</p><div id="list" style="margin-top:22px"></div>';
    const orders = await API.get("/api/orders");
    if (!orders.length){ document.getElementById("list").innerHTML = "<div class='empty'>No orders yet. <a href='malls.html' style='text-decoration:underline'>Start shopping</a></div>"; return; }
    document.getElementById("list").innerHTML = orders.map(o => {
      const eta = o.eta && new Date(o.eta) > new Date() && o.stage < 3
        ? '<div class="eta">'+I.clock+" Estimated arrival in ~"+Math.max(5,Math.round((new Date(o.eta)-new Date())/60000))+" min</div>" : "";
      return '<div class="card order-card" data-id="'+o._id+'" style="cursor:pointer">'+
        '<div class="order-top"><div><span class="num">'+esc(o.order_number)+'</span><span class="date">'+new Date(o.created_at).toLocaleDateString()+"</span>"+
        '<div class="meta">'+o.store_count+" stores &middot; "+o.item_count+" items</div></div>"+
        '<div class="amount"><b>'+money(o.total)+"</b><span>incl. delivery</span></div></div>"+
        trackerHTML(o.stage)+eta+
        (o.master_qr ? '<div class="qr-row"><img src="/api/qr/'+o.master_qr+'/svg" alt="QR"><div><b>Master QR receipt</b><p>Warehouse scans this to consolidate packages</p></div></div>' : "")+
        "</div>";
    }).join("");
    document.querySelectorAll(".order-card").forEach(c =>
      c.addEventListener("click",()=>location.href="order.html?id="+c.dataset.id));
  },

  async order(){
    const me = await getMe(); headerInit(me);
    if (!me) return requireAuth("orders.html");
    const id = new URLSearchParams(location.search).get("id");
    const main = document.getElementById("main");
    let data;
    try { data = await API.get("/api/orders/"+id); }
    catch(e){ main.innerHTML = "<div class='empty'>Order not found.</div>"; return; }
    const o = data.order;
    main.innerHTML = '<a class="back" href="orders.html">&lsaquo; Back to orders</a>'+
      '<h1 class="page">'+esc(o.order_number)+"</h1>"+
      '<p class="page-sub">'+o.merchants.length+" stores &middot; "+money(o.pricing.total)+" &middot; "+esc(o.order_status)+"</p>"+
      '<div class="card" style="margin-top:20px">'+trackerHTML(data.stage)+
      '<div style="padding:0 24px 20px" class="sumrow"><span>Paid '+money(o.pricing.subtotal)+" + delivery "+money(o.pricing.delivery_fee)+"</span><b>"+money(o.pricing.total)+"</b></div></div>"+
      "<h2 style='margin-top:30px;font-size:20px'>Store packages</h2>"+
      '<div class="packages">'+data.packages.map(p => {
        const m = o.merchants.find(x=>x.store_id===p.store_id);
        return '<div class="card pkg"><b>'+esc(m?m.store_name_snapshot:"Store")+'</b><div class="st">Package '+esc(p.package_number)+" &middot; "+esc(p.status)+"</div>"+
          (p.qr_code ? '<div class="qr-box"><img src="/api/qr/'+p.qr_code+'/svg" alt="package QR"></div>' : "")+"</div>";
      }).join("")+"</div>"+
      (data.master_qr ? '<div class="card qr-row" style="margin-top:22px"><img src="/api/qr/'+data.master_qr+'/svg"><div><b>Master QR receipt</b><p>Hub scans this to consolidate all packages</p></div></div>' : "")+
      (data.tracking.length ? '<div class="card timeline"><h3 style="font-size:16px;margin-bottom:14px">Delivery tracking</h3>'+
        data.tracking.map(t => '<div class="tl-item"><div class="tl-dot"></div><div><b>'+esc(t.status.replace(/_/g," "))+'</b><div class="when">'+new Date(t.timestamp).toLocaleString()+(t.notes?" &middot; "+esc(t.notes):"")+"</div></div></div>").join("")+"</div>" : "")+
      (data.cancellable ? '<button class="btn danger" id="cancel" style="margin-top:24px">Cancel order</button>' : "");
    const c = document.getElementById("cancel");
    if (c) c.addEventListener("click", async ()=>{
      if (!confirm("Cancel this order? Reserved stock is released and your wallet is refunded.")) return;
      try { await API.post("/api/orders/"+id+"/cancel"); toast("Order cancelled and refunded"); PAGES.order(); }
      catch(e){ toast(e.message); }
    });
  },

  async login(){
    const main = document.getElementById("main");
    const next = new URLSearchParams(location.search).get("next")||"index.html";
    main.innerHTML = '<div class="card auth-card"><h2>Welcome back</h2><p class="sub">Sign in to shop and track orders.</p>'+
      '<div class="field"><label>Email</label><input id="email" type="email"></div>'+
      '<div class="field"><label>Password</label><input id="pw" type="password"></div>'+
      '<button class="btn wide" id="go">Sign in</button>'+
      '<a class="center-link" href="register.html">New here? Create an account</a>'+
      '<a class="center-link" href="demo.html">or try the guided demo</a></div>';
    const go = async () => {
      try { await API.post("/api/auth/login",{email:document.getElementById("email").value.trim(),
        password:document.getElementById("pw").value}); location.href = next; }
      catch(e){ toast(e.message); }
    };
    document.getElementById("go").addEventListener("click", go);
    main.addEventListener("keydown", e => { if (e.key==="Enter") go(); });
  },

  async register(){
    const main = document.getElementById("main");
    const next = new URLSearchParams(location.search).get("next")||"malls.html";
    main.innerHTML = '<div class="card auth-card"><h2>Create your account</h2><p class="sub">Step 01 of your first haul.</p>'+
      '<div class="field"><label>First name</label><input id="fn"></div>'+
      '<div class="field"><label>Last name</label><input id="ln"></div>'+
      '<div class="field"><label>Email</label><input id="email" type="email"></div>'+
      '<div class="field"><label>Phone</label><input id="phone" placeholder="+27..."></div>'+
      '<div class="field"><label>Password (8+ chars, letters and numbers)</label><input id="pw" type="password"></div>'+
      '<button class="btn wide" id="go">Create account</button>'+
      '<a class="center-link" href="login.html">Already registered? Sign in</a></div>';
    document.getElementById("go").addEventListener("click", async ()=>{
      try {
        await API.post("/api/auth/register",{
          first_name:document.getElementById("fn").value.trim(),
          last_name:document.getElementById("ln").value.trim(),
          email:document.getElementById("email").value.trim(),
          phone:document.getElementById("phone").value.trim(),
          password:document.getElementById("pw").value});
        location.href = next;
      } catch(e){ toast(e.message); }
    });
  },

  async demo(){
    const me = await getMe(); headerInit(me);
    const main = document.getElementById("main");
    main.innerHTML = '<div class="card panel"><div class="kicker-sm">'+I.play+" GUIDED DEMO</div>"+
      "<h2>Watch one order travel the full pipeline</h2>"+
      "<p class='sub'>This drives the real backend: store fulfillment, hub consolidation, QR codes, and the quantum-inspired courier assignment.</p>"+
      '<div class="flowbar">'+["Paid","Stores accept","Packing","Ready","Hub receives","Consolidated","Dispatch + assign","Out for delivery","Delivered"].map(s=>"<span>"+s+"</span>").join("")+"</div>"+
      '<div style="display:flex;gap:10px;flex-wrap:wrap">'+
      (me?"":'<button class="btn" id="demologin">Sign in as demo shopper</button>')+
      '<button class="btn" id="advance" '+(me?"":"disabled")+'>Advance lifecycle</button>'+
      '<button class="btn ghost" id="state">Refresh state</button></div>'+
      '<div class="log" id="log"><span style="color:#8a847d">// event log</span></div>'+
      '<pre class="log" id="report" style="display:none;color:#9fd0ff"></pre></div>';
    const log = m => { const el=document.getElementById("log"); el.textContent += "\n"+m; el.scrollTop = el.scrollHeight; };
    const showState = async () => {
      try {
        const s = await API.get("/api/demo/state");
        log("ORDER "+s.order_number+" | stores "+JSON.stringify(s.merchant_statuses)+
            " | packages "+JSON.stringify(s.package_statuses)+" | delivery "+s.delivery_status);
      } catch(e){ log("state: "+e.message); }
    };
    const dl = document.getElementById("demologin");
    if (dl) dl.addEventListener("click", async ()=>{
      try { await API.post("/api/demo/login"); toast("Signed in as Demo Shopper"); PAGES.demo(); }
      catch(e){ toast(e.message); }
    });
    document.getElementById("state").addEventListener("click", showState);
    document.getElementById("advance").addEventListener("click", async ()=>{
      try {
        const r = await API.post("/api/demo/advance");
        (r.events||[]).forEach(log);
        if (r.optimizer_report){
          const rep = document.getElementById("report");
          rep.style.display = "block";
          rep.textContent = "QUANTUM OPTIMIZER REPORT\n"+JSON.stringify(r.optimizer_report,null,2);
        }
        if (r.stage==="DONE") log("Order delivered. View it under Orders.");
      } catch(e){ log("error: "+e.message); }
    });
    if (me) showState();
  },

  async security(){
    const me = await getMe(); headerInit(me);
    const cards = [
      ["1. Requirements","Abuse cases written per feature (duplicate checkout, cart theft, courier spoofing). Every abuse case has a server-side rejection."],
      ["2. Design","STRIDE threat model per domain. Data classification: PII, financial, operational. Nothing sensitive in QR payloads."],
      ["3. Implementation","PBKDF2-SHA256 hashing; HttpOnly + SameSite cookies; Pydantic + MongoDB $jsonSchema dual validation; Decimal128 money; idempotency keys; atomic guarded stock reservation; no string-built queries."],
      ["4. Testing","Auth failure paths, illegal state transitions rejected server-side, duplicate-checkout replay returns the same order, rate limits on auth and money endpoints."],
      ["5. Deployment","Secrets via environment variables only; Atlas IP allow-list and least-privilege DB user; secure cookie flag behind TLS."],
      ["6. Response","Immutable audit_logs for every state change; breach runbook: rotate credentials, invalidate sessions, notify affected users (POPIA-aligned)."],
    ];
    document.getElementById("main").innerHTML =
      '<h1 class="page">Security &amp; the SSDLC</h1>'+
      "<p class='page-sub'>Security is built into every phase of how MallHaul is made, not bolted on at the end.</p>"+
      '<div class="flowbar" style="margin-top:18px">'+["Requirements","Design","Implementation","Testing","Deployment","Response"].map(s=>"<span>"+s+"</span>").join("")+"</div>"+
      '<div class="sec-grid">'+cards.map(c=>'<div class="card sec-card"><h3>'+c[0]+"</h3><p>"+c[1]+"</p></div>").join("")+"</div>"+
      '<div class="card sec-card" style="margin-top:20px"><h3>Ethics &amp; data protection (POPIA-aligned)</h3><ul>'+
      "<li>Minimal PII: only what delivery and support genuinely need; password hashes never leave the database layer.</li>"+
      "<li>Couriers are paid per completed delivery; the optimizer minimises distance, which also limits unpaid travel time.</li>"+
      "<li>Audit trail protects stores and customers equally in disputes.</li>"+
      "<li>Roadmap: post-quantum TLS (ML-KEM hybrid) for wallet traffic - see docs/QUANTUM.md.</li></ul></div>"+
      "<p class='page-sub' style='margin-top:18px'>Full policy: <b>docs/SSDLC.md</b> in the repository.</p>";
  },
};

(async function boot(){
  const page = document.body.dataset.page;
  headerInit(await getMe());
  footer();
  const fn = PAGES[page];
  if (fn){ try { await fn.call(PAGES); } catch(e){ toast(e.message); } }
})();