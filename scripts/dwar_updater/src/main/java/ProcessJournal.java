package app;

import java.sql.*;
import java.util.Properties;
import java.util.ArrayList;
import java.util.List;

import com.actelion.research.chem.IDCodeParser;
import com.actelion.research.chem.StereoMolecule;
import com.actelion.research.chem.MolfileCreator;

public class ProcessJournal {

    private static final String DB_URL = "jdbc:postgresql://localhost:5433/archive_db";
    private static final String USER = "chemist";
    private static final String PASSWORD = "archive_pass";

    // Оптимальный размер пачки для работы с миллионником
    private static final int CHUNK_SIZE = 10000;

    static {
        java.util.TimeZone.setDefault(java.util.TimeZone.getTimeZone("UTC"));
        System.setProperty("user.timezone", "UTC");
    }

    public static void main(String[] args) {
        System.out.println("=== STARTING RESET AND MASSIVE CONVERSION ===");

        Properties props = new Properties();
        props.setProperty("user", USER);
        props.setProperty("password", PASSWORD);

        IDCodeParser parser = new IDCodeParser();

        String resetQuery  = "UPDATE public.archive_reactions SET raw_rxn_file = NULL;";

        String selectQuery = "SELECT id, dwar_rxncode, dwar_coordinates " +
                "FROM public.archive_reactions " +
                "WHERE dwar_rxncode IS NOT NULL " +
                "  AND dwar_rxncode != '' " +
                "  AND raw_rxn_file IS NULL " +
                "LIMIT ?;";

        String updateQuery = "UPDATE public.archive_reactions SET raw_rxn_file = ? WHERE id = ?;";

        try (Connection conn = DriverManager.getConnection(DB_URL, props)) {

            // --- ЭТАП 1: ПОЛНАЯ ЗАЧИСТКА ---
            System.out.println("Очищаем колонку raw_rxn_file для всех 3 млн записей... Подожди немного...");
            conn.setAutoCommit(true); // Для быстрой очистки одной командой
            try (Statement resetStmt = conn.createStatement()) {
                int resetRows = resetStmt.executeUpdate(resetQuery);
                System.out.println("Зачистка успешно завершена. Сброшено строк: " + resetRows);
            } catch (SQLException e) {
                System.err.println("[WARN] Ошибка при зачистке таблицы (возможно, таймаут). Пробуем продолжить без сброса...");
            }

            // --- ЭТАП 2: МАССОВЫЙ ПРОГОН С КОНВЕРТАЦИЕЙ ---
            System.out.println("\nНачинаем обработку с чистого листа...");
            conn.setAutoCommit(false); // Включаем транзакции для пакетной вставки

            try (PreparedStatement selectStmt = conn.prepareStatement(selectQuery);
                 PreparedStatement updateStmt = conn.prepareStatement(updateQuery)) {

                long totalProcessed = 0;

                while (true) {
                    selectStmt.setInt(1, CHUNK_SIZE);
                    int rowsInChunk = 0;

                    try (ResultSet rs = selectStmt.executeQuery()) {
                        while (rs.next()) {
                            rowsInChunk++;
                            long rowId = rs.getLong("id");
                            String rxnCode = rs.getString("dwar_rxncode");
                            String coords = rs.getString("dwar_coordinates");

                            if (rxnCode == null || rxnCode.trim().isEmpty()) {
                                updateStmt.setString(1, "");
                                updateStmt.setLong(2, rowId);
                                updateStmt.addBatch();
                                continue;
                            }
                            if (coords == null) coords = "";

                            try {
                                // 1. Разбиваем координаты
                                String[] coordsArray = coords.split(" ");

                                // 2. Парсим rxncode с учётом склейки '!'
                                String[] initialCodes = rxnCode.split(" ");
                                List<String> finalCodesList = new ArrayList<>();
                                int productIndexInList = -1;

                                for (String code : initialCodes) {
                                    String trimmed = code.trim();
                                    if (trimmed.isEmpty()) continue;

                                    if (trimmed.contains("!")) {
                                        if (trimmed.startsWith("!")) {
                                            productIndexInList = finalCodesList.size();
                                            finalCodesList.add(trimmed.substring(1));
                                        } else {
                                            String[] subParts = trimmed.split("!");
                                            finalCodesList.add(subParts[0]);
                                            productIndexInList = finalCodesList.size();
                                            finalCodesList.add(subParts[1]);
                                        }
                                    } else {
                                        finalCodesList.add(trimmed);
                                    }
                                }

                                List<String> reactantMolfiles = new ArrayList<>();
                                List<String> productMolfiles = new ArrayList<>();

                                // 3. Перебираем коды и координаты
                                for (int i = 0; i < finalCodesList.size(); i++) {
                                    String currentCode = finalCodesList.get(i);
                                    String currentCoord = (i < coordsArray.length) ? coordsArray[i].trim() : "";

                                    if (currentCode.length() < 2) continue;

                                    StereoMolecule mol = new StereoMolecule();
                                    parser.parse(mol, currentCode, currentCoord);

                                    MolfileCreator creator = new MolfileCreator(mol);
                                    String molfile = creator.getMolfile();

                                    if (productIndexInList != -1 && i >= productIndexInList) {
                                        productMolfiles.add(molfile);
                                    } else {
                                        reactantMolfiles.add(molfile);
                                    }
                                }

                                if (reactantMolfiles.isEmpty() || productMolfiles.isEmpty()) {
                                    throw new Exception("Разделение не удалось. Реагентов: "
                                            + reactantMolfiles.size() + ", Продуктов: " + productMolfiles.size());
                                }

                                // 4. Сборка RXN текста
                                StringBuilder rxnText = new StringBuilder();
                                rxnText.append("$RXN\n\n      OpenChemLib V2000 Reaction\n\n");
                                rxnText.append(String.format("%3d%3d\n", reactantMolfiles.size(), productMolfiles.size()));

                                for (String molfile : reactantMolfiles) {
                                    rxnText.append("$MOL\n").append(molfile);
                                }
                                for (String molfile : productMolfiles) {
                                    rxnText.append("$MOL\n").append(molfile);
                                }

                                updateStmt.setString(1, rxnText.toString());

                            } catch (Exception e) {
                                // Записываем пустую строку при ошибке, чтобы строка больше не выбиралась
                                System.err.printf("[WARN] Ошибка на ID %d: %s. Запись пустой строки.\n", rowId, e.getMessage());
                                updateStmt.setString(1, "");
                            }

                            updateStmt.setLong(2, rowId);
                            updateStmt.addBatch();
                        }
                    }

                    if (rowsInChunk == 0) {
                        System.out.println("\n=== ОБРАБОТКА ПОЛНОСТЬЮ ЗАВЕРШЕНА! ===");
                        break;
                    }

                    // Коммитим пачку в базу
                    updateStmt.executeBatch();
                    conn.commit();

                    totalProcessed += rowsInChunk;
                    System.out.println("Успешно отправлено в БД. Всего обработано строк: " + totalProcessed);
                }
            }

        } catch (SQLException e) {
            System.err.println("\n[CRITICAL SQL ERROR] Сбой цикличного обновления базы данных.");
            e.printStackTrace();
        }
    }
}