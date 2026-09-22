/**
 * Josh Tuition Centre — Mobile App (PWA)
 * Vanilla JS single-page app served at /mobile, talks to
 * /api/method/tution_center.mobile_api.* endpoints.
 */
(function () {
  "use strict";

  // ------------------------------------------------------------------
  // boot state from server-rendered attributes
  // ------------------------------------------------------------------
  var appEl = document.getElementById("app");
  var STATE = {
    loggedIn: appEl.dataset.loggedIn === "1",
    csrf: appEl.dataset.csrf || "",
    fullname: appEl.dataset.fullname || "",
    isTeacher: appEl.dataset.isTeacher === "1",
    activeTab: "home",
    me: null,
    activeStudent: null,
    currency: "INR",
    cache: {}, // tab -> payload (stale-while-revalidate)
  };

  var API = "/api/method/tution_center.mobile_api.";

  // ------------------------------------------------------------------
  // tiny helpers
  // ------------------------------------------------------------------
  function $(sel) { return document.querySelector(sel); }
  function $all(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  function show(el) { if (el) el.classList.remove("hidden"); }
  function hide(el) { if (el) el.classList.add("hidden"); }

  function toast(msg, isErr) {
    var t = $("#toast");
    t.textContent = msg;
    t.classList.toggle("error", !!isErr);
    show(t);
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { hide(t); }, 2600);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function money(v) {
    v = Number(v || 0);
    return STATE.currency + " " + v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  }

  function fmtDate(d) {
    if (!d) return "—";
    var dt = new Date(d + (d.length === 10 ? "T00:00:00" : ""));
    if (isNaN(dt.getTime())) return d;
    return dt.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  }

  function fmtTime(t) {
    if (!t) return "";
    var parts = String(t).split(":");
    var h = parseInt(parts[0], 10), m = parts[1] || "00";
    var ampm = h >= 12 ? "PM" : "AM";
    var h12 = h % 12 || 12;
    return h12 + ":" + m + " " + ampm;
  }

  // ------------------------------------------------------------------
  // API layer — frappe-style X-Frappe-CSRF-Token
  // ------------------------------------------------------------------
  function api(fn, args, method) {
    args = args || {};
    var opts = {
      method: method || "POST",
      headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": STATE.csrf },
      credentials: "same-origin",
    };
    if (method === "GET") {
      var qs = Object.keys(args).map(function (k) {
        return encodeURIComponent(k) + "=" + encodeURIComponent(args[k] == null ? "" : args[k]);
      }).join("&");
      opts.method = "GET";
      delete opts.body;
      if (qs) opts.url = API + fn + "?" + qs;
    } else {
      opts.body = JSON.stringify(args);
    }
    var url = opts.url || API + fn;
    return fetch(url, opts).then(function (res) {
      return res.json().then(function (data) {
        if (data.exc) {
          var msg = "Request failed";
          try { msg = JSON.parse(data.exc)[0]; } catch (e) { /* keep default */ }
          var err = new Error(msg);
          err.exc = data.exc;
          throw err;
        }
        if (!res.ok) throw new Error(data._server_messages ? JSON.parse(data._server_messages)[0] : msg2(data));
        return data.message;
      });
    });

    function msg2(d) {
      try {
        var m = JSON.parse(d._server_messages);
        var x = JSON.parse(m[0]);
        return x.message || "Request failed";
        } catch (e) { return "Request failed"; }
    }
  }

  // ----------------------------------------------------------------
  // login / logout
  // ----------------------------------------------------------------
  function bindLoginForm() {
    var form = $("#login-form");
    if (!form) return;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = $("#login-btn");
      btn.disabled = true;
      btn.textContent = "Signing in…";
      var fd = new FormData(form);
      var body = "usr=" + encodeURIComponent(fd.get("usr")) + "&pwd=" + encodeURIComponent(fd.get("pwd"));
      fetch("/api/method/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body,
      }).then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.message && data.message !== "Logged In" && data.home_page) { /* some setups */ }
          if (data.exc || data.message === "Invalid login" ) { throw new Error("Invalid email or password"); }
          return fetch("/mobile", { credentials: "same-origin" })
            .then(function (r) { return r.text(); })
            .then(function (html) {
              evalShell(html);
              bootApp();
            });
        })
      .catch(function (err) {
        show($("#login-error"));
        $("#login-error").textContent = err.message || "Login failed";
        btn.disabled = false;
        btn.textContent = "Sign In";
      });
    });
  }

  function evalShell(html) {
    var doc = new DOMParser().parseFromString(html, "text/html");
    var newApp = doc.getElementById("app");
    if (newApp) {
      appEl.parentNode.replaceChild(newApp, appEl);
      appEl = newApp;
      STATE.csrf = newApp.dataset.csrf || "";
      STATE.loggedIn = newApp.dataset.loggedIn === "1";
      STATE.fullname = newApp.dataset.fullname || "";
      STATE.isTeacher = newApp.dataset.isTeacher === "1";
    }
  }

  // ------------------------------------------------------------------
  // render helpers
  // ------------------------------------------------------------------
  function avatarHtml(photo, name) {
    var initials = (name || "?").trim().split(/\s+/).map(function (p) { return p[0]; })
      .slice(0, 2).join("").toUpperCase();
    if (photo) {
      return '<img class="avatar" src="' + esc(photo) + '" alt="" />';
    }
    return '<div class="avatar">' + esc(initials || "?") + '</div>';
  }

  function statusPill(status) {
    var cls = {
      Paid: "ok", Active: "ok", Present: "ok", Resolved: "ok", Closed: "ok", Pass: "ok",
      Unpaid: "bad", Absent: "bad", Fail: "bad", Suspended: "bad", Reopened: "bad",
      "Partially Paid": "warn", Leave: "warn", "In Progress": "warn", Assigned: "warn",
    }[status] || "muted";
    return '<span class="pill ' + cls + '">' + esc(status || "—") + "</span>";
  }

  function empty(msg) {
    return '<div class="empty">📭<br>' + esc(msg) + "</div>";
  }

  function card(inner, cls) {
    return '<div class="card ' + (cls || "") + '">' + inner + "</div>";
  }

  // ------------------------------------------------------------------
  // screens
  // ------------------------------------------------------------------
  var Screens = {
    // ---------------- home ----------------
    home: function () {
      return api("get_me", {}, "GET").then(function (me) {
        STATE.me = me;
        STATE.currency = me.currency || "INR";
        if (!STATE.activeStudent && me.default_student) {
          STATE.activeStudent = me.default_student;
        }
        var p = me.summary || {};
        var headerName = me.is_teacher ? (p.teacher && p.teacher.teacher_name) : (p.student && p.student.student_name);
        $("#header-name").textContent = headerName || me.fullname || "";
        $("#header-role").textContent = me.is_teacher ? "Teacher" : (me.students.length > 1 ? "Guardian" : "Student");
        $("#header-avatar").outerHTML = avatarHtml(
          me.is_teacher ? p.teacher && p.teacher.photo : p.student && p.student.photo,
          headerName
        );

        var html = "";

        // student switcher (guardian with multiple children)
        if (me.students.length > 1) {
          html += '<div class="switcher">' + me.students.map(function (s) {
            return '<button class="switch-btn' + (s.id === STATE.activeStudent ? " active" : "") +
              '" data-student="' + esc(s.id) + '">' + esc(s.name) + "</button>";
          }).join("") + "</div>";
        }

        if (me.is_teacher) {
          html += Screens._teacherHome(p);
        } else {
          html += Screens._studentHome(me, p);
        }

        // announcements
        html += '<h3 class="sec-title">📣 Announcements</h3>';
        html += card('<div id="ann-list"><div class="empty small">Loading…</div></div>');
        $("#content").innerHTML = html;
        bindSwitcher();
        Screens._loadAnnouncements();
      });
    },

    _studentHome: function (me, p) {
      var s = p.student || {};
      var html = "";

      html += card(
        '<div class="due-hero ' + (p.outstanding > 0 ? "due" : "clear") + '">' +
        '<div class="due-label">Outstanding Fees</div>' +
        '<div class="due-amount">' + money(p.outstanding) + "</div>" +
        '<div class="due-sub">Attendance ' + (p.attendance_pct || 0) + "% · " +
        (p.attendance_marked || 0) + ' classes recorded</div></div>'
      );

      // today's classes
      var tc = p.today_classes || { day: "", slots: [] };
      html += '<h3 class="sec-title">🗓 Today · ' + esc(tc.day) + "</h3>";
      if (tc.slots.length) {
        html += tc.slots.map(function (sl) {
          return card(
            '<div class="row"><span class="row-main">' + esc(sl.course) + "</span>" +
            '<span class="row-side">' + fmtTime(sl.start_time) + " – " + fmtTime(sl.end_time) + "</span></div>" +
            '<div class="row-sub">Room ' + esc(sl.room || "—") + " · " + esc(sl.teacher || "") + "</div>",
            "slim"
          );
        }).join("");
      } else {
        html += card(empty("No classes scheduled today"), "slim");
      }

      // quick stats
      html += '<div class="grid2">';
      html += card(
        '<div class="stat"><div class="stat-num">' + esc(s.grade_level || "—") + '</div><div class="stat-label">Grade</div></div>' +
        '<div class="stat"><div class="stat-num">' + esc(s.status || "—") + '</div><div class="stat-label">Status</div></div>',
        "slim"
      );
      html += "</div>";

      // batches
      if (p.batches && p.batches.length) {
        html += '<h3 class="sec-title">🎓 My Batches</h3>';
        html += p.batches.map(function (b) {
          return card(
            '<div class="row"><span class="row-main">' + esc(b.batch_name || b.name) + "</span>" +
            statusPill(b.status) + "</div>" +
            '<div class="row-sub">' + esc(b.course) + (b.teacher ? " · " + esc(b.teacher) : "") + "</div>",
            "slim"
          );
        }).join("");
      }
      return html;
    },

    _teacherHome: function (p) {
      var t = p.teacher || {};
      var html = card(
        '<div class="due-hero clear"><div class="due-label">My Batches</div>' +
        '<div class="due-amount">' + (p.batches || []).length + '</div>' +
        '<div class="due-sub">' + (p.total_students || 0) + ' students · ' +
        ((p.today_classes || {}).slots || []).length + ' classes today</div></div>'
      );
      var tc = p.today_classes || { day: "", slots: [] };
      html += '<h3 class="sec-title">🗓 Today · ' + esc(tc.day) + "</h3>";
      if (tc.slots.length) {
        html += tc.slots.map(function (sl) {
          return card(
            '<div class="row"><span class="row-main">' + esc(sl.course) + "</span>" +
            '<span class="row-side">' + fmtTime(sl.start_time) + "</span></div>" +
            '<div class="row-sub">Room ' + esc(sl.room || "—") + " · " + esc(sl.batch) + "</div>",
            "slim"
          );
        }).join("");
      } else {
        html += card(empty("No classes scheduled today"), "slim");
      }
      if (p.batches && p.batches.length) {
        html += '<h3 class="sec-title">👥 My Batches</h3>';
        html += p.batches.map(function (b) {
          return card(
            '<div class="row"><span class="row-main">' + esc(b.batch_name) + "</span>" +
            '<span class="row-side">' + b.student_count + "/" + b.max_seats + " seats</span></div>" +
            '<div class="row-sub">' + esc(b.course) + "</div>",
            "slim"
          );
        }).join("");
      }
      return html;
    },

    _loadAnnouncements: function () {
      var host = $("#ann-list");
      if (!host) return;
      api("get_announcements", {}, "GET").then(function (anns) {
        if (!anns.length) { host.innerHTML = empty("No announcements"); return; }
        host.innerHTML = anns.map(function (a) {
          return card(
            '<div class="row"><span class="row-main">' + (a.pinned ? "📌 " : "") + esc(a.title) + "</span>" +
            '<span class="row-side">' + fmtDate(a.publish_date) + "</span></div>" +
            '<div class="row-sub clamp3">' + esc(String(a.message || "").replace(/<[^>]*>/g, " ")) + "</div>",
            "slim"
          );
        }).join("");
      }).catch(function () { host.innerHTML = empty("Could not load announcements"); });
    },

    // ---------------- fees ----------------
    fees: function () {
      if (STATE.me && STATE.me.is_teacher) {
        $("#content").innerHTML = empty("Teachers do not have a fee view");
        return Promise.resolve();
      }
      var sid = STATE.activeStudent;
      return api("get_fees", { student_id: sid || "" }, "GET").then(function (data) {
        STATE.currency = data.currency || STATE.currency;
        var t = data.totals;
        var html = card(
          '<div class="due-hero ' + (t.outstanding > 0 ? "due" : "clear") + '">' +
          '<div class="due-label">Outstanding</div>' +
          '<div class="due-amount">' + money(t.outstanding) + "</div>" +
          '<div class="due-sub">Billed ' + money(t.fee) + " · Paid " + money(t.paid) + "</div></div>"
        );
        html += '<h3 class="sec-title">💳 Payment History</h3>';
        if (data.payments.length) {
          html += data.payments.slice(0, 10).map(function (pay) {
            return card(
              '<div class="row"><span class="row-main">' + money(pay.amount) + "</span>" +
              '<span class="row-side">' + fmtDate(pay.payment_date) + "</span></div>" +
              '<div class="row-sub">' + esc(pay.mode_of_payment || "Payment") +
              (pay.reference_no ? " · Ref " + esc(pay.reference_no) : "") + "</div>",
              "slim"
            );
          }).join("");
        } else {
          html += card(empty("No payments yet"), "slim");
        }
        html += '<h3 class="sec-title">📄 Fee Ledger</h3>';
        if (data.enrolments.length) {
          html += data.enrolments.map(function (e) {
            var pct = e.fee_amount ? Math.min(100, Math.round(e.paid_amount / e.fee_amount * 100)) : 0;
            return card(
              '<div class="row"><span class="row-main">' + esc(e.course || e.name) + "</span>" + statusPill(e.status) + "</div>" +
              '<div class="row-sub">' + esc(e.academic_term || "") + " · Due " + fmtDate(e.due_date) + "</div>" +
              '<div class="progress"><div class="progress-bar" style="width:' + pct + '%"></div></div>' +
              '<div class="row-sub">' + money(e.paid_amount) + " of " + money(e.fee_amount) +
              " · Balance <b>" + money(e.outstanding_amount) + "</b></div>",
              "slim"
            );
          }).join("");
        } else {
          html += card(empty("No fees billed yet"), "slim");
        }
        $("#content").innerHTML = html;
      });
    },

    // ---------------- timetable ----------------
    timetable: function () {
      return api("get_timetable", { batch: "" }, "GET").then(function (data) {
        if (!data.slots.length) {
          $("#content").innerHTML = empty("No timetable published for your batch yet");
          return;
        }
        var days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
        var byDay = {};
        data.slots.forEach(function (s) { (byDay[s.day] = byDay[s.day] || []).push(s); });
        var today = new Date().toLocaleDateString("en-GB", { weekday: "long" });
        var html = '<div class="chip-row">' +
          '<span class="chip">' + esc(data.batch_name) + "</span></div>";
        days.forEach(function (d) {
          if (!byDay[d]) return;
          html += '<h3 class="sec-title">' + esc(d) + (d === today ? " · today" : "") + "</h3>";
          html += byDay[d].map(function (s) {
            return card(
              '<div class="row"><span class="row-main">' + esc(s.course) + "</span>" +
              '<span class="row-side">' + fmtTime(s.start_time) + " – " + fmtTime(s.end_time) + "</span></div>" +
              '<div class="row-sub">Room ' + esc(s.room || "—") +
              (s.teacher ? " · " + esc(s.teacher) : "") + "</div>",
              "slim"
            );
          }).join("");
        });
        $("#content").innerHTML = html;
      });
    },

    // ---------------- results ----------------
    results: function () {
      if (STATE.me && STATE.me.is_teacher) {
        $("#content").innerHTML = empty("Use the desk to enter exam results");
        return Promise.resolve();
      }
      var sid = STATE.activeStudent;
      return api("get_results", { student_id: sid || "" }, "GET").then(function (data) {
        var st = data.stats;
        var html = '<div class="grid3">' +
          card('<div class="stat"><div class="stat-num">' + st.pass + '</div><div class="stat-label">Pass</div></div>', "slim") +
          card('<div class="stat"><div class="stat-num">' + st.fail + '</div><div class="stat-label">Fail</div></div>', "slim") +
          card('<div class="stat"><div class="stat-num">' + st.avg_pct + '%</div><div class="stat-label">Avg</div></div>', "slim") +
          "</div>";
        if (!data.results.length) {
          html += empty("No results published yet");
        } else {
          html += data.results.map(function (r) {
            return card(
              '<div class="row"><span class="row-main">' + esc(r.course) + "</span>" + statusPill(r.result) + "</div>" +
              '<div class="row-sub">' + esc(r.exam) + " · " + fmtDate(r.exam_date) + "</div>" +
              '<div class="row-sub">' + r.marks_obtained + " / " + r.max_marks +
              (r.percentage != null ? " · " + r.percentage + "%" : "") +
              (r.grade ? " · Grade " + esc(r.grade) : "") + "</div>",
              "slim"
            );
          }).join("");
        }
        $("#content").innerHTML = html;
      });
    },

    // ---------------- more ----------------
    more: function () {
      var sid = STATE.activeStudent;
      var me = STATE.me || {};
      var html = "";

      html += '<h3 class="sec-title">👤 Profile</h3>';
      html += '<div id="profile-host"><div class="empty small">Loading…</div></div>';

      html += '<h3 class="sec-title">🗓 Attendance (90 days)</h3>';
      html += '<div id="att-host"><div class="empty small">Loading…</div></div>';

      html += '<h3 class="sec-title">📚 Assignments</h3>';
      html += '<div id="asg-host"><div class="empty small">Loading…</div></div>';

      if (!me.is_teacher) {
        html += '<h3 class="sec-title">🆘 Raise a Complaint</h3>';
        html += card(
          '<form id="complaint-form">' +
          '<label class="field"><span>Subject</span><input name="subject" required /></label>' +
          '<label class="field"><span>Type</span><select name="type">' +
          ["Academic", "Fees", "Faculty", "Facility", "Discipline", "Other"].map(function (t) {
            return "<option>" + t + "</option>";
          }).join("") +
          '</select></label>' +
          '<label class="field"><span>Details</span><textarea name="description" rows="3" required></textarea></label>' +
          '<button class="btn-primary" type="submit">Submit Complaint</button></form>'
        );
      }

      html += '<h3 class="sec-title">⚙︎ More</h3>';
      html += card(
        '<button class="list-btn" id="install-btn">📲 Install App on Home Screen</button>' +
        '<button class="list-btn" id="logout-btn">↩︎ Sign Out</button>'
      );

      $("#content").innerHTML = html;

      Screens._loadProfile();
      Screens._loadAttendance();
      Screens._loadAssignments();
      Screens._bindComplaint();
      $("#install-btn").addEventListener("click", promptInstall);
      $("#logout-btn").addEventListener("click", function () {
        fetch("/api/method/logout", { method: "POST", credentials: "same-origin" })
          .then(function () { location.reload(); });
      });
    },

    _loadProfile: function () {
      var host = $("#profile-host");
      if (!host) return;
      if (STATE.me && STATE.me.is_teacher) {
        host.innerHTML = card(
          '<div class="row"><span class="row-main">' + esc((STATE.me.summary.teacher || {}).teacher_name || "") + "</span></div>" +
          '<div class="row-sub">Teacher</div>', "slim");
        return;
      }
      api("get_student_profile", { student_id: sid0() }, "GET").then(function (p) {
        var s = p.student;
        host.innerHTML = card(
          '<div class="row"><span class="row-main">' + esc(s.student_name) + "</span>" + statusPill(s.status) + "</div>" +
          '<div class="row-sub">' + esc(s.grade_level || "—") + " · " + esc(s.school || "—") + "</div>" +
          '<div class="row-sub">✉ ' + esc(s.student_email_id || "—") + " · ☎ " + esc(s.student_mobile_number || "—") + "</div>" +
          '<div class="row-sub">Joined ' + fmtDate(s.joining_date) + "</div>", "slim"
        ) + (p.guardians.length ?
          '<div class="row-sub pad">Guardians: ' + p.guardians.map(function (g) {
            return esc(g.guardian_name) + " (" + esc(g.relationship || "—") + ")";
          }).join(", ") + "</div>" : "");
      }).catch(function (e) { host.innerHTML = empty(e.message); });

      function sid0() { return STATE.activeStudent || ""; }
    },

    _loadAttendance: function () {
      var host = $("#att-host");
      if (!host) return;
      api("get_attendance", { student_id: STATE.activeStudent || "" }, "GET").then(function (a) {
        var html = '<div class="grid3">' +
          card('<div class="stat"><div class="stat-num">' + a.percentage + '%</div><div class="stat-label">Present</div></div>', "slim") +
          card('<div class="stat"><div class="stat-num">' + a.absent + '</div><div class="stat-label">Absent</div></div>', "slim") +
          card('<div class="stat"><div class="stat-num">' + a.leave + '</div><div class="stat-label">Leave</div></div>', "slim") +
          "</div>";
        if (a.records.length) {
          html += a.records.slice(0, 15).map(function (r) {
            return card(
              '<div class="row"><span class="row-main">' + fmtDate(r.date) + "</span>" + statusPill(r.status) + "</div>",
              "slim"
            );
          }).join("");
        } else {
          html += empty("No attendance recorded");
        }
        host.innerHTML = html;
      }).catch(function (e) { host.innerHTML = empty(e.message); });
    },

    _loadAssignments: function () {
      var host = $("#asg-host");
      if (!host) return;
      if (STATE.me && STATE.me.is_teacher) {
        host.innerHTML = empty("Open the desk to manage assignments");
        return;
      }
      api("get_assignments", { student_id: STATE.activeStudent || "" }, "GET").then(function (d) {
        if (!d.assignments.length) { host.innerHTML = empty("No assignments"); return; }
        host.innerHTML = d.assignments.map(function (a) {
          var sub = a.my_submission;
          return card(
            '<div class="row"><span class="row-main">' + esc(a.title) + "</span>" + statusPill(sub ? sub.status : a.status) + "</div>" +
            '<div class="row-sub">' + esc(a.course) + " · Due " + fmtDate(a.due_date) +
            (sub && sub.score != null ? " · Score " + sub.score + "/" + a.max_score : "") + "</div>",
            "slim"
          );
        }).join("");
      }).catch(function (e) { host.innerHTML = empty(e.message); });
    },

    _bindComplaint: function () {
      var f = $("#complaint-form");
      if (!f) return;
      f.addEventListener("submit", function (e) {
        e.preventDefault();
        var fd = new FormData(f);
        api("create_complaint", {
          subject: fd.get("subject"),
          type: fd.get("type"),
          description: fd.get("description"),
          student: STATE.activeStudent || "",
        }).then(function () {
          toast("Complaint submitted — the centre will contact you");
          f.reset();
        }).catch(function (e) { toast(e.message, true); });
      });
    },
  };

  // ------------------------------------------------------------------
  // router
  // ------------------------------------------------------------------
  function switchTab(tab) {
    STATE.activeTab = tab;
    $all(".tab").forEach(function (b) {
      b.classList.toggle("active", b.dataset.tab === tab);
    });
    $("#content").innerHTML =
      '<div class="skeleton"><div class="skel-card"></div><div class="skel-card"></div></div>';
    hide($("#toast"));
    var p = Screens[tab] ? Screens[tab]() : Promise.resolve();
    Promise.resolve(p).catch(function (err) {
      $("#content").innerHTML = empty(err.message || "Something went wrong");
      if (err.message === "Please log in") showLogin();
    });
  }

  function bindSwitcher() {
    $all(".switch-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        STATE.activeStudent = b.dataset.student;
        $all(".switch-btn").forEach(function (x) { x.classList.toggle("active", x === b); });
        Screens._loadAnnouncements && Screens._loadAnnouncements();
        switchTab("home");
      });
    });
  }

  function bindTabbar() {
    $all(".tab").forEach(function (b) {
      b.addEventListener("click", function () { switchTab(b.dataset.tab); });
    });
    $("#refresh-btn").addEventListener("click", function () { switchTab(STATE.activeTab); });
  }

  // ------------------------------------------------------------------
  // login screen / boot
  // ------------------------------------------------------------------
  function showLogin() {
    show($("#login-screen"));
    hide($("#main-screen"));
  }

  function bootApp() {
    hide($("#login-screen"));
    show($("#main-screen"));
    bindTabbar();
    // deep link ?tab=fees
    var params = new URLSearchParams(location.search);
    var tab = params.get("tab");
    switchTab(tab && Screens[tab] ? tab : "home");
  }

  // PWA install prompt
  var deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
  });
  function promptInstall() {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then(function () { deferredPrompt = null; });
    } else {
      toast("Open browser menu → “Add to Home Screen”");
    }
  }

  // service worker (best-effort; install-to-home-screen works even without it
  // on modern Chrome/Edge. When wrapped with Capacitor this is a no-op.)
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker
        .register("/assets/tution_center/js/tuition_sw.js")
        .catch(function () { /* scope not allowed — PWA install still works */ });
    });
  }

  // ------------------------------------------------------------------
  // start
  // ------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    if (STATE.loggedIn) {
      bootApp();
    } else {
      showLogin();
      bindLoginForm();
    }
  });
})();
