import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowUpRight,
  Bell,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  Clock3,
  Download,
  LayoutDashboard,
  Leaf,
  LogOut,
  MapPin,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Truck,
  Users,
} from "lucide-react";
import {
  api,
  type Analytics,
  type Complaint,
  type Config,
  type Notice,
  type User,
} from "./api";
import WasteMap from "./Map";
import "./style.css";

const title = (s: string) =>
  s
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
const date = (s: string) =>
  new Date(s).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
const streams = ["WET", "DRY", "SANITARY", "SPECIAL_CARE", "UNKNOWN_MIXED"];
const roles = [
  "CITIZEN",
  "WASTE_COLLECTOR",
  "SUPERVISOR",
  "GOVERNMENT_AUTHORITY",
];
const priorities = ["LOW", "NORMAL", "HIGH", "URGENT"];
const statuses = [
  "SUBMITTED",
  "UNDER_REVIEW",
  "VERIFIED",
  "ASSIGNED",
  "ACCEPTED",
  "IN_PROGRESS",
  "RESOLUTION_SUBMITTED",
  "RESOLUTION_VERIFIED",
  "CLOSED",
  "REOPENED",
  "REJECTED",
];
type Run = (action: () => Promise<void>) => Promise<void>;

function App() {
  const [user, setUser] = useState<User | null>(null),
    [boot, setBoot] = useState(true),
    [config, setConfig] = useState<Config>({
      wards: [],
      categories: [],
      sla: [],
    }),
    [view, setView] = useState("Overview"),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [tick, setTick] = useState(0),
    [selected, setSelected] = useState<number | null>(null),
    [notices, setNotices] = useState<Notice[]>([]);
  const run: Run = async (action) => {
    setError("");
    setBusy(true);
    try {
      await action();
    } catch (e) {
      setMessage("");
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setBoot(false));
  }, []);
  useEffect(() => {
    if (user) {
      Promise.all([api<Config>("/config"), api<Notice[]>("/notifications")])
        .then(([c, n]) => {
          setConfig(c);
          setNotices(n);
        })
        .catch((e) => setError(e.message));
    }
  }, [user, tick]);
  const refresh = () => setTick((x) => x + 1);
  const open = (id: number) => {
    setSelected(id);
    setView("Complaint detail");
  };
  if (boot) return <div className="loading">Loading CleanCity…</div>;
  if (!user)
    return <Login onLogin={setUser} run={run} error={error} busy={busy} />;
  const management = ["SUPERVISOR", "GOVERNMENT_AUTHORITY"].includes(user.role);
  const nav = [
    ["Overview", LayoutDashboard],
    ["Complaints", ClipboardList],
    ["Map & hotspots", MapPin],
    ...(management ? [["Insights & reports", ShieldCheck]] : []),
    ["Notifications", Bell],
    ...(user.role === "GOVERNMENT_AUTHORITY"
      ? [["People & settings", Settings]]
      : []),
    ["Profile", Users],
  ] as const;
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brandmark">
            <Leaf size={23} />
          </span>
          <div>
            CleanCity<small>WASTE OPERATIONS</small>
          </div>
        </div>
        <div className="workspace-label">MUNICIPAL WORKSPACE</div>
        <nav>
          {nav.map(([name, Icon]) => (
            <button
              key={name as string}
              className={view === name ? "nav active" : "nav"}
              onClick={() => {
                setView(name as string);
                setSelected(null);
                setError("");
                setMessage("");
              }}
            >
              <Icon size={19} />
              {name as string}
              {name === "Notifications" && notices.some((n) => !n.read) && (
                <span className="dot" />
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="impact">
            <Leaf size={24} />
            <strong>
              Cleaner streets.
              <br />
              Stronger communities.
            </strong>
            <p>Every resolved report makes a difference.</p>
          </div>
          <div className="identity">
            <span className="avatar">{user.name[0]}</span>
            <div>
              <strong>{user.name.split(" · ")[0]}</strong>
              <small>{title(user.role)}</small>
            </div>
            <button
              aria-label="Sign out"
              onClick={() =>
                run(async () => {
                  await api("/auth/logout", "POST");
                  setUser(null);
                  setMessage("");
                  setView("Overview");
                })
              }
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <span>
            Workspace <ChevronRight size={14} /> <strong>{view}</strong>
          </span>
          <div>
            <span className="demo-label">
              {config.demo ? "LOCAL DEMONSTRATION" : "MUNICIPAL OPERATIONS"}
            </span>
            <button
              className="mobile-logout"
              aria-label="Sign out on mobile"
              onClick={() =>
                run(async () => {
                  await api("/auth/logout", "POST");
                  setUser(null);
                  setMessage("");
                  setView("Overview");
                })
              }
            >
              <LogOut size={17} />
            </button>
            <button
              aria-label="Open notifications"
              onClick={() => setView("Notifications")}
            >
              <Bell size={19} />
            </button>
          </div>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">SMART WASTE MANAGEMENT</div>
              <h1>
                {view === "Overview"
                  ? management
                    ? "A cleaner city starts here."
                    : "Your community, cared for."
                  : view}
              </h1>
              <p>
                {view === "Overview"
                  ? "A clear view of reports, field operations and the work ahead."
                  : `${title(user.role)} workspace · accountable action, from report to resolution.`}
              </p>
            </div>
            {user.role === "CITIZEN" && (
              <button
                className="primary"
                onClick={() => setView("Report waste")}
              >
                <Plus size={17} /> Report waste
              </button>
            )}
          </div>
          {error && (
            <div role="alert" className="alert error">
              {error}
              <button onClick={() => setError("")}>Dismiss</button>
            </div>
          )}
          {message && (
            <div role="status" className="alert success">
              {message}
              <button onClick={() => setMessage("")}>Dismiss</button>
            </div>
          )}
          {busy && (
            <div role="status" className="working">
              Saving changes…
            </div>
          )}
          {selected && view === "Complaint detail" ? (
            <Detail
              id={selected}
              user={user}
              config={config}
              run={run}
              refresh={refresh}
              tick={tick}
              busy={busy}
              message={setMessage}
            />
          ) : view === "Report waste" ? (
            <Report
              config={config}
              run={run}
              busy={busy}
              done={(c) => {
                refresh();
                open(c.id);
                setMessage(
                  c.possible_duplicates
                    ? `Report created. ${c.possible_duplicates} nearby recent report(s) may concern the same issue. Your report remains valid.`
                    : "Report created. Add a photograph below to help the supervisor verify it.",
                );
              }}
            />
          ) : view === "Notifications" ? (
            <section className="panel">
              <h2>Updates for you</h2>
              {!notices.length && <Empty text="No notifications yet." />}
              {notices.map((n) => (
                <div
                  key={n.id}
                  className={"notice " + (!n.read ? "unread" : "")}
                >
                  <Bell size={18} />
                  <div>
                    <button
                      className="text-button"
                      onClick={() => open(n.complaint_id)}
                    >
                      {n.message}
                    </button>
                    <small>{date(n.created_at)}</small>
                  </div>
                  {!n.read && (
                    <button
                      className="secondary"
                      onClick={() =>
                        run(async () => {
                          await api(`/notifications/${n.id}/read`, "POST");
                          refresh();
                        })
                      }
                    >
                      Mark read
                    </button>
                  )}
                </div>
              ))}
            </section>
          ) : view === "People & settings" ? (
            <Administration
              config={config}
              run={run}
              refresh={refresh}
              busy={busy}
            />
          ) : view === "Profile" ? (
            <section className="panel narrow">
              <h2>Your profile</h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  run(async () => {
                    setUser(
                      await api<User>("/auth/me", "PATCH", {
                        name: f.get("name"),
                      }),
                    );
                    setMessage("Profile updated.");
                  });
                }}
              >
                <label>
                  Name
                  <input
                    name="name"
                    defaultValue={user.name}
                    minLength={2}
                    maxLength={100}
                    required
                  />
                </label>
                <label>
                  Email
                  <input value={user.email} disabled />
                </label>
                <label>
                  Role
                  <input value={title(user.role)} disabled />
                </label>
                <button disabled={busy} className="primary">
                  Save profile
                </button>
              </form>
            </section>
          ) : (
            <Workspace
              user={user}
              config={config}
              view={view}
              tick={tick}
              open={open}
              run={run}
            />
          )}
          <footer>
            CleanCity{" "}
            <span>
              Smart Waste Management and Monitoring System · B.Tech project
            </span>
            <span>
              <ShieldCheck size={14} /> Role-protected workspace
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}

function Login({
  onLogin,
  run,
  error,
  busy,
}: {
  onLogin: (u: User) => void;
  run: Run;
  error: string;
  busy: boolean;
}) {
  const [register, setRegister] = useState(false),
    [registered, setRegistered] = useState(false);
  return (
    <div className="login">
      <section className="login-story">
        <div className="brand">
          <span className="brandmark">
            <Leaf />
          </span>
          CleanCity
        </div>
        <div>
          <div className="eyebrow">BETTER PLACES TO LIVE</div>
          <h1>
            Small reports.
            <br />
            Lasting change.
          </h1>
          <p>
            Connecting citizens and city teams to make every neighbourhood
            cleaner, safer and better cared for.
          </p>
          <div className="journey">
            <span>
              <MapPin />
              Report
            </span>
            <i />
            <span>
              <Truck />
              Resolve
            </span>
            <i />
            <span>
              <CheckCircle2 />
              Verify
            </span>
          </div>
        </div>
        <small>Smart Waste Management and Monitoring System</small>
      </section>
      <section className="login-form">
        <div className="eyebrow">YOUR CITY. YOUR IMPACT.</div>
        <h1>{register ? "Join your community" : "Welcome back"}</h1>
        <p>
          {register
            ? "Create a citizen account to report and track waste issues."
            : "Sign in to your municipal workspace."}
        </p>
        {error && (
          <div role="alert" className="alert error">
            {error}
          </div>
        )}
        {registered && (
          <div className="alert success">
            Account created. You can now sign in.
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            run(async () => {
              const data = {
                email: f.get("email"),
                password: f.get("password"),
              };
              if (register) {
                await api("/auth/register", "POST", {
                  ...data,
                  name: f.get("name"),
                });
                setRegister(false);
                setRegistered(true);
              } else onLogin(await api<User>("/auth/login", "POST", data));
            });
          }}
        >
          {register && (
            <label>
              Full name
              <input
                name="name"
                autoComplete="name"
                minLength={2}
                maxLength={100}
                required
              />
            </label>
          )}
          <label>
            Email address
            <input
              type="email"
              name="email"
              autoComplete="username"
              placeholder="you@example.com"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              name="password"
              autoComplete={register ? "new-password" : "current-password"}
              minLength={register ? 12 : 1}
              maxLength={128}
              required
            />
          </label>
          <button className="primary" disabled={busy}>
            {busy
              ? "Please wait…"
              : register
                ? "Create citizen account"
                : "Sign in"}
            <ArrowUpRight size={18} />
          </button>
        </form>
        <button className="text-button" onClick={() => setRegister(!register)}>
          {register
            ? "Already registered? Sign in"
            : "New here? Create a citizen account"}
        </button>
        <div className="login-note">
          <ShieldCheck size={20} />
          <p>
            Staff accounts are issued by the authority.
            <br />
            Local demo credentials: <strong>demo-access.txt</strong> in the
            project folder.
          </p>
        </div>
      </section>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="empty">
      <ClipboardList size={30} />
      <h3>{text}</h3>
      <p>New activity will appear here as reports move through the workflow.</p>
    </div>
  );
}
function Badge({ status }: { status: string }) {
  return (
    <span className={"badge " + status.toLowerCase()}>{title(status)}</span>
  );
}
function Bars({
  values,
  labels = {},
}: {
  values: Record<string, number>;
  labels?: Record<string, string>;
}) {
  const max = Math.max(1, ...Object.values(values));
  return Object.keys(values).length ? (
    <div className="bars">
      {Object.entries(values).map(([k, v]) => (
        <div key={k}>
          <div>
            <span>{labels[k] || title(k)}</span>
            <strong>{v}</strong>
          </div>
          <div className="bar-track">
            <i style={{ width: `${(v / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  ) : (
    <p className="muted">No data for these filters.</p>
  );
}

function Workspace({
  user,
  config,
  view,
  tick,
  open,
  run,
}: {
  user: User;
  config: Config;
  view: string;
  tick: number;
  open: (id: number) => void;
  run: Run;
}) {
  const [rows, setRows] = useState<Complaint[]>([]),
    [total, setTotal] = useState(0),
    [stats, setStats] = useState<Analytics | null>(null),
    [page, setPage] = useState(1),
    [loading, setLoading] = useState(true),
    [filter, setFilter] = useState<Record<string, string>>({});
  const management = ["SUPERVISOR", "GOVERNMENT_AUTHORITY"].includes(user.role),
    query = new URLSearchParams(
      Object.entries(filter).filter(([, v]) => v),
    ).toString();
  useEffect(() => {
    let live = true;
    setLoading(true);
    run(async () => {
      const result = await api<{ items: Complaint[]; total: number }>(
        `/complaints?${query}&page=${page}`,
      );
      const a = management ? await api<Analytics>(`/analytics?${query}`) : null;
      if (live) {
        setRows(result.items);
        setTotal(result.total);
        setStats(a);
      }
    }).finally(() => {
      if (live) setLoading(false);
    });
    return () => {
      live = false;
    };
  }, [query, page, tick, management]); // request wrapper intentionally stable in behavior
  const change = (k: string, v: string) => {
    setFilter((f) => ({ ...f, [k]: v }));
    setPage(1);
  };
  const labels = Object.fromEntries(
    config.wards.map((w) => [w.id, w.name.split(" · ")[0]]),
  );
  const isInsights = view === "Insights & reports",
    isMap = view === "Map & hotspots";
  return (
    <>
      <div className="metrics">
        <Metric
          label={management ? "Total reports" : "Your reports"}
          value={stats?.total ?? total}
          icon={<ClipboardList />}
          note="Recorded in the system"
        />
        <Metric
          label={management ? "Active operations" : "On this page · active"}
          value={
            stats?.open ??
            rows.filter(
              (c) =>
                !["CLOSED", "REJECTED", "RESOLUTION_VERIFIED"].includes(
                  c.status,
                ),
            ).length
          }
          icon={<Truck />}
          note="Moving toward resolution"
        />
        <Metric
          label={management ? "SLA compliance" : "On this page · closed"}
          value={
            management
              ? stats?.sla_compliance == null
                ? "—"
                : `${stats.sla_compliance}%`
              : rows.filter((c) => c.status === "CLOSED").length
          }
          icon={<ShieldCheck />}
          note={
            management
              ? "Verified resolutions within target"
              : "Confirmed by you"
          }
        />
        <Metric
          label={management ? "Overdue reports" : "On this page · overdue"}
          value={stats?.overdue ?? rows.filter((c) => c.overdue).length}
          icon={<Clock3 />}
          note="Requires timely attention"
          warm
        />
      </div>
      <div className="filterbar">
        <div className="search">
          <Search size={17} />
          <input
            aria-label="Search reports"
            placeholder="Search reports…"
            value={filter.search || ""}
            onChange={(e) => change("search", e.target.value)}
          />
        </div>
        <select
          aria-label="Status filter"
          onChange={(e) => change("status", e.target.value)}
        >
          <option value="">All statuses</option>
          {statuses.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          aria-label="Ward filter"
          onChange={(e) => change("ward_id", e.target.value)}
        >
          <option value="">All wards</option>
          {config.wards.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Category filter"
          onChange={(e) => change("category_id", e.target.value)}
        >
          <option value="">All categories</option>
          {config.categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Waste stream filter"
          onChange={(e) => change("waste_stream", e.target.value)}
        >
          <option value="">All waste streams</option>
          {streams.map((s) => (
            <option key={s} value={s}>
              {title(s)}
            </option>
          ))}
        </select>
        <select
          aria-label="Priority filter"
          onChange={(e) => change("priority", e.target.value)}
        >
          <option value="">All priorities</option>
          {priorities.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <label>
          From
          <input
            type="date"
            aria-label="Start date"
            onChange={(e) => change("start", e.target.value)}
          />
        </label>
        <label>
          To
          <input
            type="date"
            aria-label="End date"
            onChange={(e) => change("end", e.target.value)}
          />
        </label>
        {management && (
          <a className="secondary" href={`/api/reports.csv?${query}`}>
            <Download size={16} /> Export CSV
          </a>
        )}
      </div>
      {loading ? (
        <div className="panel loading">Loading operational data…</div>
      ) : isMap ? (
        <section className="panel">
          <div className="panel-title">
            <h2>
              {management ? "Geographic hotspots" : "Your report locations"}
            </h2>
            <span className="muted">
              {management
                ? "Historical counts · filters applied"
                : "Current page of reports"}
            </span>
          </div>
          <WasteMap
            points={
              stats
                ? stats.hotspots.map((p) => ({
                    ...p,
                    label: `${p.count} historical reports · ${p.open} unresolved`,
                  }))
                : rows.map((c) => ({ ...c, label: c.reference }))
            }
          />
          <p className="muted">
            Map tiles require internet. Coordinates remain available when the
            map provider is unavailable. Hotspots use a rounded 0.001° grid, not
            predictions.
          </p>
        </section>
      ) : isInsights && stats ? (
        <>
          <div className="two-col">
            <section className="panel">
              <h2>Report trend</h2>
              <Bars values={stats.trend} />
            </section>
            <section className="panel">
              <h2>Ward comparison</h2>
              <Bars values={stats.wards} labels={labels} />
            </section>
            <section className="panel">
              <h2>Waste streams</h2>
              <Bars values={stats.streams} />
            </section>
            <section className="panel">
              <h2>Complaint categories</h2>
              <Bars
                values={stats.categories}
                labels={Object.fromEntries(
                  config.categories.map((c) => [c.id, c.name]),
                )}
              />
            </section>
            <section className="panel">
              <h2>Resolution & service levels</h2>
              <dl>
                <dt>Average resolution time</dt>
                <dd>{stats.average_resolution_hours ?? "—"} hours</dd>
                <dt>Median resolution time</dt>
                <dd>{stats.median_resolution_hours ?? "—"} hours</dd>
                <dt>Approaching SLA deadline</dt>
                <dd>{stats.approaching}</dd>
                <dt>Escalated reports</dt>
                <dd>{stats.escalated}</dd>
                <dt>Reports reopened</dt>
                <dd>{stats.reopened}</dd>
              </dl>
            </section>
            <section className="panel">
              <h2>Collector operations</h2>
              <p className="muted">
                Current assignment ownership; workload varies by ward and
                complexity.
              </p>
              {stats.collectors.map((c) => (
                <div className="summary-row" key={c.collector_id}>
                  <span>Collector #{c.collector_id}</span>
                  <strong>
                    {c.assigned} assigned · {c.resolved} resolved
                  </strong>
                </div>
              ))}
            </section>
          </div>
        </>
      ) : (
        <>
          <div className={view === "Overview" ? "overview-grid" : ""}>
            <section className="panel reports">
              <div className="panel-title">
                <div>
                  <h2>
                    {user.role === "WASTE_COLLECTOR"
                      ? "Your assignments"
                      : "Complaint activity"}
                  </h2>
                  <p>
                    Track each report from first notice to verified resolution.
                  </p>
                </div>
                <span className="count">{total} reports</span>
              </div>
              {!rows.length ? (
                <Empty text="No reports found" />
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Report / location</th>
                        <th>Status</th>
                        <th>Priority</th>
                        <th>SLA deadline</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((c) => (
                        <tr key={c.id}>
                          <td>
                            <button
                              className="report-link"
                              onClick={() => open(c.id)}
                            >
                              {c.reference}
                            </button>
                            <span className="description">{c.description}</span>
                            <small>
                              <MapPin size={12} />
                              {labels[c.ward_id] || c.address}
                            </small>
                          </td>
                          <td>
                            <Badge status={c.status} />
                          </td>
                          <td>
                            <span
                              className={"priority " + c.priority.toLowerCase()}
                            >
                              ● {title(c.priority)}
                            </span>
                          </td>
                          <td>
                            <span className={c.overdue ? "overdue" : ""}>
                              {date(c.deadline)}
                            </span>
                            {c.overdue && (
                              <small className="overdue">Overdue</small>
                            )}
                          </td>
                          <td>
                            <button
                              aria-label={`Open ${c.reference}`}
                              onClick={() => open(c.id)}
                            >
                              <ArrowUpRight size={18} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="pagination">
                <span>
                  {total
                    ? `${(page - 1) * 20 + 1}–${Math.min(page * 20, total)} of ${total}`
                    : "0 reports"}
                </span>
                <div>
                  <button
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </button>
                  <button
                    disabled={page * 20 >= total}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </section>
            {view === "Overview" && (
              <div className="overview-side">
                <section className="panel">
                  <div className="panel-title">
                    <h2>{stats ? "Status overview" : "How it works"}</h2>
                    <span className="mini-icon">
                      <Leaf size={18} />
                    </span>
                  </div>
                  {stats ? (
                    <Bars values={stats.status} />
                  ) : (
                    <ol className="steps">
                      <li>
                        <strong>Report an issue</strong>
                        <p>Add the location and photographic evidence.</p>
                      </li>
                      <li>
                        <strong>Follow the progress</strong>
                        <p>A supervisor verifies and assigns your report.</p>
                      </li>
                      <li>
                        <strong>Confirm the result</strong>
                        <p>
                          Review the after-work evidence and share feedback.
                        </p>
                      </li>
                    </ol>
                  )}
                </section>
                <section className="green-panel">
                  <CircleHelp size={25} />
                  <h2>Evidence matters.</h2>
                  <p>
                    Before and after photographs help everyone verify that the
                    job is done.
                  </p>
                  <span>
                    Transparent from start to finish <ArrowUpRight size={17} />
                  </span>
                </section>
              </div>
            )}
          </div>
        </>
      )}
    </>
  );
}
function Metric({
  label,
  value,
  icon,
  note,
  warm = false,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  note: string;
  warm?: boolean;
}) {
  return (
    <div className={"metric " + (warm ? "warm" : "")}>
      <div>
        <span>{label}</span>
        <span className="metric-icon">{icon}</span>
      </div>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}

function Report({
  config,
  run,
  busy,
  done,
}: {
  config: Config;
  run: Run;
  busy: boolean;
  done: (c: Complaint) => void;
}) {
  const [lat, setLat] = useState(""),
    [lng, setLng] = useState(""),
    [geoError, setGeoError] = useState("");
  return (
    <section className="panel">
      <div className="panel-title">
        <div>
          <h2>Report a waste issue</h2>
          <p>
            Tell your local team what needs attention. Add evidence after
            saving.
          </p>
        </div>
        <span className="count">Citizen report</span>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          run(async () =>
            done(
              await api<Complaint>("/complaints", "POST", {
                description: f.get("description"),
                address: f.get("address"),
                ward_id: Number(f.get("ward_id")),
                category_id: Number(f.get("category_id")),
                waste_stream: f.get("waste_stream"),
                latitude: Number(lat),
                longitude: Number(lng),
              }),
            ),
          );
        }}
      >
        <div className="two-col">
          <div>
            <label>
              Complaint category
              <select name="category_id" required>
                <option value="">Select a category</option>
                {config.categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Waste stream
              <select name="waste_stream" defaultValue="UNKNOWN_MIXED">
                {streams.map((s) => (
                  <option key={s} value={s}>
                    {title(s)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              What happened?
              <textarea
                name="description"
                minLength={10}
                maxLength={4000}
                required
                placeholder="Describe the issue and any useful landmarks…"
              />
            </label>
            <label>
              Service ward
              <select name="ward_id" required>
                <option value="">Select ward</option>
                {config.wards.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Address / landmark
              <input name="address" minLength={3} maxLength={300} required />
            </label>
          </div>
          <div>
            <div className="panel-title">
              <h3>Pin the location</h3>
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  if (!navigator.geolocation) {
                    setGeoError(
                      "Geolocation is unavailable. Enter coordinates or select the map.",
                    );
                    return;
                  }
                  navigator.geolocation.getCurrentPosition(
                    (p) => {
                      setLat(String(p.coords.latitude));
                      setLng(String(p.coords.longitude));
                      setGeoError("");
                    },
                    () =>
                      setGeoError(
                        "Location unavailable. Enter coordinates or select the map.",
                      ),
                    { timeout: 10000 },
                  );
                }}
              >
                <MapPin size={15} /> Use my location
              </button>
            </div>
            {geoError && <p role="alert">{geoError}</p>}
            <WasteMap
              points={
                lat && lng
                  ? [
                      {
                        latitude: Number(lat),
                        longitude: Number(lng),
                        label: "Report location",
                      },
                    ]
                  : []
              }
              onPick={(a, b) => {
                setLat(a.toFixed(6));
                setLng(b.toFixed(6));
              }}
            />
            <div className="two-col">
              <label>
                Latitude
                <input
                  type="number"
                  step="any"
                  min="-90"
                  max="90"
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                  required
                />
              </label>
              <label>
                Longitude
                <input
                  type="number"
                  step="any"
                  min="-180"
                  max="180"
                  value={lng}
                  onChange={(e) => setLng(e.target.value)}
                  required
                />
              </label>
            </div>
            <p className="muted">
              Click the map or enter coordinates manually. Ward selection uses
              your input; demo boundaries are not official municipal boundaries.
            </p>
          </div>
        </div>
        <button disabled={busy} className="primary">
          Submit report <ArrowUpRight size={17} />
        </button>
      </form>
    </section>
  );
}

function Detail({
  id,
  user,
  config,
  run,
  refresh,
  tick,
  busy,
  message,
}: {
  id: number;
  user: User;
  config: Config;
  run: Run;
  refresh: () => void;
  tick: number;
  busy: boolean;
  message: (s: string) => void;
}) {
  const [c, setC] = useState<Complaint | null>(null),
    [reason, setReason] = useState(""),
    [priority, setPriority] = useState("NORMAL"),
    [category, setCategory] = useState(0),
    [recommend, setRecommend] = useState<
      { id: number; name: string; workload: number; score: number }[]
    >([]),
    [collector, setCollector] = useState(""),
    [pendingAction, setPendingAction] = useState<string | null>(null),
    [preview, setPreview] = useState("");
  useEffect(() => {
    run(async () => {
      const x = await api<Complaint>(`/complaints/${id}`);
      setC(x);
      setPriority(x.priority);
      setCategory(x.category_id);
      if (user.role === "SUPERVISOR")
        setRecommend(await api(`/complaints/${id}/recommendations`));
    });
  }, [id, tick]);
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );
  if (!c) return <div className="panel loading">Loading report…</div>;
  const performTransition = (action: string) =>
    run(async () => {
      await api(`/complaints/${id}/transition`, "POST", {
        action,
        version: c.version,
        reason,
        ...(action === "verify" ? { priority, category_id: category } : {}),
      });
      setPendingAction(null);
      setReason("");
      refresh();
      message("Workflow updated.");
    });
  const actions: Record<string, string[]> = {
    CITIZEN: c.status === "RESOLUTION_VERIFIED" ? ["confirm", "reopen"] : [],
    WASTE_COLLECTOR:
      c.status === "ASSIGNED"
        ? ["accept"]
        : c.status === "ACCEPTED"
          ? ["start"]
          : c.status === "IN_PROGRESS"
            ? ["submit_resolution"]
            : [],
    SUPERVISOR: ["SUBMITTED", "REOPENED"].includes(c.status)
      ? ["review", ...(c.status === "SUBMITTED" ? ["reject"] : [])]
      : c.status === "UNDER_REVIEW"
        ? ["verify", "reject"]
        : c.status === "RESOLUTION_SUBMITTED"
          ? ["approve", "return"]
          : [],
    GOVERNMENT_AUTHORITY: [],
  };
  const stages =
    user.role === "CITIZEN" && ["SUBMITTED", "UNDER_REVIEW"].includes(c.status)
      ? ["COMPLAINT"]
      : user.role === "WASTE_COLLECTOR" &&
          ["ACCEPTED", "IN_PROGRESS"].includes(c.status)
        ? ["BEFORE", ...(c.status === "IN_PROGRESS" ? ["AFTER"] : [])]
        : [];
  return (
    <>
      <section className="panel">
        <div className="panel-title">
          <div>
            <div className="eyebrow">{c.reference}</div>
            <h2>
              {config.categories.find((x) => x.id === c.category_id)?.name}
            </h2>
          </div>
          <Badge status={c.status} />
        </div>
        <p className="detail-description">{c.description}</p>
        <div className="detail-meta">
          <span>
            <MapPin size={16} />
            {c.address}
          </span>
          <span>{title(c.waste_stream)}</span>
          <span className={"priority " + c.priority.toLowerCase()}>
            {title(c.priority)} priority
          </span>
          <span className={c.overdue ? "overdue" : ""}>
            Due {date(c.deadline)}
          </span>
        </div>
      </section>
      <div className="two-col detail-grid">
        <div>
          <section className="panel">
            <h2>Workflow actions</h2>
            {!actions[user.role]?.length && (
              <p className="muted">
                No status actions for your role at this stage.
              </p>
            )}
            {(actions[user.role]?.length > 0 || user.role === "SUPERVISOR") && (
              <>
                <label>
                  Reason / completion notes
                  <textarea
                    value={reason}
                    maxLength={2000}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Explain the action, resolution or reason for return…"
                  />
                </label>
                {user.role === "SUPERVISOR" && c.status === "UNDER_REVIEW" && (
                  <div className="two-col">
                    <label>
                      Verified priority
                      <select
                        value={priority}
                        onChange={(e) => setPriority(e.target.value)}
                      >
                        {priorities.map((p) => (
                          <option key={p}>{p}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Verified category
                      <select
                        value={category}
                        onChange={(e) => setCategory(Number(e.target.value))}
                      >
                        {config.categories.map((x) => (
                          <option key={x.id} value={x.id}>
                            {x.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                )}
                <div className="actions">
                  {actions[user.role]?.map((action) => (
                    <button
                      key={action}
                      disabled={busy}
                      className={
                        ["reject", "return", "reopen"].includes(action)
                          ? "secondary"
                          : "primary"
                      }
                      onClick={() =>
                        ["reject", "return", "reopen", "confirm"].includes(
                          action,
                        )
                          ? setPendingAction(action)
                          : performTransition(action)
                      }
                    >
                      {title(action)}
                    </button>
                  ))}
                </div>
                {pendingAction && (
                  <div
                    className="confirmation"
                    role="group"
                    aria-label="Confirm workflow action"
                  >
                    <h3>{title(pendingAction)} this complaint?</h3>
                    <p>
                      {pendingAction === "confirm"
                        ? "This closes the complaint. Check the resolution evidence before continuing."
                        : "This action will be recorded in the complaint history with your reason."}
                    </p>
                    <div className="actions">
                      <button
                        className="secondary"
                        disabled={busy}
                        onClick={() => setPendingAction(null)}
                      >
                        Cancel action
                      </button>
                      <button
                        className="primary"
                        disabled={busy}
                        onClick={() => performTransition(pendingAction)}
                      >
                        Yes, {title(pendingAction).toLowerCase()}
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
            {user.role === "SUPERVISOR" &&
              ["VERIFIED", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"].includes(
                c.status,
              ) && (
                <div className="assignment">
                  <h3>Assign a collector</h3>
                  <p className="muted">
                    Recommendations favour eligible collectors with fewer active
                    jobs.
                  </p>
                  <label>
                    Collector
                    <select
                      value={collector}
                      onChange={(e) => setCollector(e.target.value)}
                    >
                      <option value="">Choose a collector</option>
                      {recommend.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name} · {r.workload} jobs · score {r.score}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="primary"
                    disabled={busy || !collector}
                    onClick={() =>
                      run(async () => {
                        await api(`/complaints/${id}/assign`, "POST", {
                          collector_id: Number(collector),
                          version: c.version,
                          reason,
                        });
                        refresh();
                        message("Assignment saved and collector notified.");
                      })
                    }
                  >
                    Save assignment
                  </button>
                </div>
              )}
          </section>
          <section className="panel">
            <h2>Photographic evidence</h2>
            <p className="muted">
              JPEG, PNG or WebP · up to 5 MB. Location metadata is removed.
              Fresh before and after images are required for each work cycle.
            </p>
            {stages.length > 0 && (
              <form
                className="upload"
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  const stage = f.get("stage");
                  f.delete("stage");
                  run(async () => {
                    await api(
                      `/complaints/${id}/evidence?stage=${stage}`,
                      "POST",
                      f,
                    );
                    refresh();
                    message("Evidence uploaded.");
                    setPreview("");
                  });
                }}
              >
                <label>
                  Evidence stage
                  <select name="stage">
                    {stages.map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Image
                  <input
                    name="file"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    required
                    onChange={(e) => {
                      if (e.target.files?.[0])
                        setPreview(URL.createObjectURL(e.target.files[0]));
                    }}
                  />
                </label>
                {preview && (
                  <img
                    className="preview"
                    src={preview}
                    alt="Selected evidence preview"
                  />
                )}
                <button disabled={busy} className="secondary">
                  Upload evidence
                </button>
              </form>
            )}
            <div className="evidence-grid">
              {c.evidence?.map((e) => (
                <figure key={e.id}>
                  <a
                    href={`/api/evidence/${e.id}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <img
                      src={`/api/evidence/${e.id}`}
                      alt={`${title(e.stage)} evidence for work cycle ${e.cycle + 1}`}
                    />
                  </a>
                  <figcaption>
                    {title(e.stage)} · cycle {e.cycle + 1}
                  </figcaption>
                </figure>
              ))}
            </div>
            {!c.evidence?.length && (
              <p className="muted">No evidence uploaded yet.</p>
            )}
          </section>
          {user.role === "CITIZEN" && c.status === "CLOSED" && (
            <section className="panel">
              <h2>How did we do?</h2>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  run(async () => {
                    await api(`/complaints/${id}/feedback`, "POST", {
                      rating: Number(f.get("rating")),
                      comment: f.get("comment"),
                    });
                    message("Thank you. Your feedback has been recorded.");
                  });
                }}
              >
                <label>
                  Rating
                  <select name="rating">
                    {[5, 4, 3, 2, 1].map((n) => (
                      <option key={n} value={n}>
                        {n} / 5
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Feedback
                  <textarea name="comment" maxLength={1000} />
                </label>
                <button className="primary" disabled={busy}>
                  Send feedback
                </button>
              </form>
            </section>
          )}
        </div>
        <div>
          <section className="panel">
            <h2>Report location</h2>
            <WasteMap points={[{ ...c, label: c.reference }]} />
            <p className="muted">
              {c.latitude.toFixed(6)}, {c.longitude.toFixed(6)}
            </p>
            <a
              className="text-button"
              href={`https://www.openstreetmap.org/?mlat=${c.latitude}&mlon=${c.longitude}#map=17/${c.latitude}/${c.longitude}`}
              target="_blank"
              rel="noreferrer"
            >
              Open location map ↗
            </a>
          </section>
          <section className="panel">
            <h2>Activity timeline</h2>
            <ol className="timeline">
              {c.history?.map((h, i) => (
                <li key={i}>
                  <span />
                  <strong>{title(h.status)}</strong>
                  <small>{date(h.created_at)}</small>
                  <p>{h.reason}</p>
                </li>
              ))}
            </ol>
          </section>
          {!!c.assignments?.length && (
            <section className="panel">
              <h2>Assignment history</h2>
              {c.assignments.map((a, i) => (
                <div className="summary-row" key={i}>
                  <span>
                    Collector #{a.collector_id}
                    <small>{date(a.created_at)}</small>
                  </span>
                  <p>{a.reason}</p>
                </div>
              ))}
            </section>
          )}
        </div>
      </div>
    </>
  );
}

function Administration({
  config,
  run,
  refresh,
  busy,
}: {
  config: Config;
  run: Run;
  refresh: () => void;
  busy: boolean;
}) {
  const [people, setPeople] = useState<User[]>([]),
    [audit, setAudit] = useState<
      {
        id: number;
        action: string;
        entity: string;
        detail: string;
        created_at: string;
      }[]
    >([]),
    [page, setPage] = useState(1);
  const reload = async () => {
    setPeople(await api<User[]>("/users"));
    setAudit(await api(`/audit?page=${page}`));
  };
  useEffect(() => {
    run(reload);
  }, [page]);
  return (
    <>
      <div className="two-col">
        <section className="panel">
          <h2>Create a staff account</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              run(async () => {
                await api("/users", "POST", {
                  name: f.get("name"),
                  email: f.get("email"),
                  password: f.get("password"),
                  role: f.get("role"),
                  ward_id: f.get("ward_id") ? Number(f.get("ward_id")) : null,
                });
                await reload();
              });
            }}
          >
            <label>
              Full name
              <input name="name" required minLength={2} />
            </label>
            <label>
              Email
              <input name="email" type="email" required />
            </label>
            <label>
              Initial password
              <input
                name="password"
                type="password"
                minLength={12}
                maxLength={128}
                required
                autoComplete="new-password"
              />
            </label>
            <div className="two-col">
              <label>
                Role
                <select name="role">
                  {roles.map((r) => (
                    <option key={r}>{r}</option>
                  ))}
                </select>
              </label>
              <label>
                Ward
                <select name="ward_id">
                  <option value="">No operational ward</option>
                  {config.wards.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <button className="primary" disabled={busy}>
              Create account
            </button>
          </form>
        </section>
        <section className="panel">
          <h2>Service configuration</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              run(async () => {
                await api("/config/wards", "POST", {
                  name: f.get("name"),
                  zone: f.get("zone"),
                });
                refresh();
              });
            }}
          >
            <h3>Add ward</h3>
            <label>
              Ward name
              <input name="name" required minLength={2} />
            </label>
            <label>
              Zone
              <input name="zone" required minLength={2} />
            </label>
            <button disabled={busy} className="secondary">
              Add ward
            </button>
          </form>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              run(async () => {
                await api("/config/categories", "POST", {
                  name: f.get("name"),
                });
                refresh();
              });
            }}
          >
            <h3>Add complaint category</h3>
            <label>
              Category name
              <input name="name" required minLength={2} />
            </label>
            <button disabled={busy} className="secondary">
              Add category
            </button>
          </form>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              run(async () => {
                await api("/config/sla", "PUT", {
                  priority: f.get("priority"),
                  hours: Number(f.get("hours")),
                });
                refresh();
              });
            }}
          >
            <h3>SLA policy</h3>
            <p className="muted">
              {config.sla.map((s) => `${s.priority}: ${s.hours}h`).join(" · ")}.
              Changes apply to future deadline calculations.
            </p>
            <div className="two-col">
              <label>
                Priority
                <select name="priority">
                  {priorities.map((p) => (
                    <option key={p}>{p}</option>
                  ))}
                </select>
              </label>
              <label>
                Resolution hours
                <input type="number" name="hours" min={1} max={720} required />
              </label>
            </div>
            <button disabled={busy} className="secondary">
              Update SLA
            </button>
          </form>
        </section>
      </div>
      <section className="panel">
        <h2>People</h2>
        {people.map((p) => (
          <div className="notice" key={p.id}>
            <span className="avatar">{p.name[0]}</span>
            <div>
              <strong>{p.name}</strong>
              <small>
                {title(p.role)} · {p.email}
              </small>
            </div>
            <button
              disabled={busy}
              className="secondary"
              onClick={() =>
                run(async () => {
                  await api(`/users/${p.id}`, "PATCH", {
                    active: !p.active,
                    available: p.available,
                  });
                  await reload();
                })
              }
            >
              {p.active ? "Deactivate" : "Activate"}
            </button>
            {p.role === "WASTE_COLLECTOR" && (
              <button
                disabled={busy}
                className="secondary"
                onClick={() =>
                  run(async () => {
                    await api(`/users/${p.id}`, "PATCH", {
                      active: p.active,
                      available: !p.available,
                    });
                    await reload();
                  })
                }
              >
                {p.available ? "Mark unavailable" : "Mark available"}
              </button>
            )}
          </div>
        ))}
      </section>
      <section className="panel">
        <h2>Audit trail</h2>
        {audit.map((a) => (
          <div className="summary-row" key={a.id}>
            <div>
              <strong>{a.action}</strong>
              <small>
                {date(a.created_at)} · entity {a.entity}
              </small>
            </div>
            <span>{a.detail}</span>
          </div>
        ))}
        <div className="pagination">
          <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span>Page {page}</span>
          <button
            disabled={audit.length < 50}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      </section>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
