import { Navigate, Outlet, RouterProvider, createBrowserRouter } from "react-router-dom";
import { AppProvider, useApp } from "./AppContext";
import { AttemptPage } from "./pages/AttemptPage";
import { ExamPage } from "./pages/ExamPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { MyPage } from "./pages/MyPage";
import { ReportPage } from "./pages/ReportPage";

function ProtectedRoute() {
  const { profile } = useApp();
  return profile ? <Outlet /> : <Navigate to="/login" replace />;
}

export const createAppRouter = () =>
  createBrowserRouter([
    { path: "/login", element: <LoginPage /> },
    {
      element: <ProtectedRoute />,
      children: [
        { path: "/", element: <HomePage /> },
        { path: "/exam/:roomCode", element: <ExamPage /> },
        { path: "/my", element: <MyPage /> },
        { path: "/my/attempts/:attemptId", element: <AttemptPage /> },
        { path: "/my/attempts/:attemptId/report", element: <ReportPage /> },
      ],
    },
    { path: "*", element: <Navigate to="/" replace /> },
  ]);

const appRouter = createAppRouter();

export default function App() {
  return (
    <AppProvider>
      <RouterProvider router={appRouter} />
    </AppProvider>
  );
}
