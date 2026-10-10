import { lazy } from 'react';

const HomePage = lazy(() => import('../pages/HomePage').then((module) => ({ default: module.HomePage })));
const FuentesList = lazy(() => import('../pages/FuentesList').then((module) => ({ default: module.FuentesList })));
const FuenteForm = lazy(() => import('../pages/FuenteForm').then((module) => ({ default: module.FuenteForm })));
const DataQualityDashboard = lazy(() => import('../pages/DataQualityDashboard').then((module) => ({ default: module.DataQualityDashboard })));
const PublicProcesados = lazy(() => import('../pages/PublicProcesados').then((module) => ({ default: module.PublicProcesados })));
const PublicContratoDetalle = lazy(() => import('../pages/PublicContratoDetalle').then((module) => ({ default: module.PublicContratoDetalle })));
const PublicDashboard = lazy(() => import('../pages/PublicDashboard').then((module) => ({ default: module.PublicDashboard })));
const AdminLogin = lazy(() => import('../pages/admin/AdminLogin'));
const AdminDashboard = lazy(() => import('../pages/admin/AdminDashboard'));
const AdminSyncLogs = lazy(() => import('../pages/admin/AdminSyncLogs'));
const AdminReprocesamiento = lazy(() => import('../pages/admin/AdminReprocesamiento').then((module) => ({ default: module.AdminReprocesamiento })));
const AdminAnalitica = lazy(() => import('../pages/admin/AdminAnalitica').then((module) => ({ default: module.AdminAnalitica })));

export function HomePageRoute() { return <HomePage />; }
export function FuentesListRoute() { return <FuentesList />; }
export function FuenteFormRoute() { return <FuenteForm />; }
export function DataQualityDashboardRoute() { return <DataQualityDashboard />; }
export function PublicProcesadosRoute() { return <PublicProcesados />; }
export function PublicContratoDetalleRoute() { return <PublicContratoDetalle />; }
export function PublicDashboardRoute() { return <PublicDashboard />; }
export function AdminLoginRoute() { return <AdminLogin />; }
export function AdminDashboardRoute() { return <AdminDashboard />; }
export function AdminSyncLogsRoute() { return <AdminSyncLogs />; }
export function AdminReprocesamientoRoute() { return <AdminReprocesamiento />; }
export function AdminAnaliticaRoute() { return <AdminAnalitica />; }
